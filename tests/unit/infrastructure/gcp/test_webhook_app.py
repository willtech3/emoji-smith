from __future__ import annotations

import importlib
import json
import sys
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient
from google.cloud import pubsub_v1


@pytest.fixture()
def webhook_app_module(monkeypatch):
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-test")
    monkeypatch.setenv("SLACK_SIGNING_SECRET", "signing-secret")
    monkeypatch.setenv("PUBSUB_PROJECT", "test-project")
    monkeypatch.setenv("PUBSUB_TOPIC", "emoji-smith-jobs")

    mock_publisher = MagicMock()
    mock_publisher.topic_path.return_value = (
        "projects/test-project/topics/emoji-smith-jobs"
    )
    monkeypatch.setattr(
        pubsub_v1,
        "PublisherClient",
        MagicMock(return_value=mock_publisher),
    )

    module_name = "emojismith.infrastructure.gcp.webhook_app"
    if module_name in sys.modules:
        del sys.modules[module_name]
    return importlib.import_module(module_name)


@pytest.mark.unit()
class TestWebhookApp:
    def test_health_endpoint_returns_healthy(self, webhook_app_module):
        client = TestClient(webhook_app_module.app)
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "healthy", "service": "webhook"}

    def test_url_verification_returns_challenge_without_signature(
        self, webhook_app_module
    ):
        client = TestClient(webhook_app_module.app)
        resp = client.post(
            "/slack/events",
            content=b'{"type":"url_verification","challenge":"abc"}',
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 200
        assert resp.json() == {"challenge": "abc"}

    def test_message_action_opens_modal(self, webhook_app_module):
        # Arrange: bypass signature validation and Slack API network calls
        webhook_app_module.webhook_handler._security_service.is_authentic_webhook = (  # type: ignore[attr-defined]
            MagicMock(return_value=True)
        )
        event_processor = webhook_app_module.webhook_handler._event_processor  # type: ignore[attr-defined]
        event_processor._slack_repo.open_modal = AsyncMock()  # type: ignore[attr-defined]

        client = TestClient(webhook_app_module.app)
        payload = {
            "type": "message_action",
            "trigger_id": "trigger_123",
            "message": {"text": "hello", "user": "U123", "ts": "123.456"},
            "channel": {"id": "C123"},
            "team": {"id": "T123"},
        }

        # Act
        resp = client.post(
            "/slack/events",
            content=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )

        # Assert
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}
        event_processor._slack_repo.open_modal.assert_awaited_once()  # type: ignore[attr-defined]


@pytest.mark.unit()
class TestWebhookAppSubmission:
    def test_view_submission_enqueues_job(self, webhook_app_module):
        webhook_app_module.webhook_handler._security_service.is_authentic_webhook = (  # type: ignore[attr-defined]
            MagicMock(return_value=True)
        )
        event_processor = webhook_app_module.webhook_handler._event_processor  # type: ignore[attr-defined]
        event_processor._job_queue.enqueue_job = AsyncMock(return_value="msg-123")  # type: ignore[attr-defined]

        client = TestClient(webhook_app_module.app)

        payload = {
            "type": "view_submission",
            "view": {
                "private_metadata": json.dumps(
                    {
                        "message_text": "hello",
                        "user_id": "U123",
                        "channel_id": "C123",
                        "timestamp": "123.456",
                        "team_id": "T123",
                    }
                ),
                "state": {
                    "values": {
                        "emoji_description": {"description": {"value": "facepalm"}},
                        "image_provider_block": {
                            "image_provider_select": {
                                "selected_option": {"value": "openai"}
                            }
                        },
                    }
                },
            },
        }

        resp = client.post(
            "/slack/interactive",
            content=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )

        assert resp.status_code == 200
        assert resp.json() == {"response_action": "clear"}

        event_processor._job_queue.enqueue_job.assert_awaited_once()  # type: ignore[attr-defined]
        enqueued_job = event_processor._job_queue.enqueue_job.call_args.args[0]  # type: ignore[attr-defined]
        assert enqueued_job.user_description == "facepalm"
        assert enqueued_job.image_provider == "openai"
