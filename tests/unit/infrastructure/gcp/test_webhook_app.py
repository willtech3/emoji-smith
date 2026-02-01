from __future__ import annotations

import importlib
import json
import re
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient
from google.cloud import pubsub_v1

from emojismith.application.handlers.slack_webhook_handler import (
    SlackWebhookHandler,
    WebhookEventProcessor,
)
from emojismith.domain.services.webhook_security_service import WebhookSecurityService
from shared.domain.repositories import JobQueueProducer, SlackModalRepository


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

    return importlib.import_module("emojismith.infrastructure.gcp.webhook_app")


@pytest.fixture()
def webhook_test_client(webhook_app_module):
    slack_repo = AsyncMock(spec=SlackModalRepository)
    job_queue = AsyncMock(spec=JobQueueProducer)

    security_service = MagicMock(spec=WebhookSecurityService)
    security_service.is_authentic_webhook.return_value = True

    processor = WebhookEventProcessor(
        slack_repo=slack_repo,
        job_queue=job_queue,
        google_enabled=True,
    )
    handler = SlackWebhookHandler(
        security_service=security_service,
        event_processor=processor,
    )

    app = webhook_app_module.create_app(webhook_handler=handler)
    client = TestClient(app)
    return client, slack_repo, job_queue


@pytest.mark.unit()
class TestWebhookApp:
    def test_health_endpoint_returns_healthy(self, webhook_test_client):
        client, _slack_repo, _job_queue = webhook_test_client
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "healthy", "service": "webhook"}

    def test_url_verification_returns_challenge_without_signature(
        self, webhook_test_client
    ):
        client, _slack_repo, _job_queue = webhook_test_client
        resp = client.post(
            "/slack/events",
            content=b'{"type":"url_verification","challenge":"abc"}',
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 200
        assert resp.json() == {"challenge": "abc"}

    def test_message_action_opens_modal(self, webhook_test_client):
        client, slack_repo, _job_queue = webhook_test_client
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
        slack_repo.open_modal.assert_awaited_once()


@pytest.mark.unit()
class TestWebhookAppSubmission:
    def test_view_submission_enqueues_job(self, webhook_test_client):
        client, _slack_repo, job_queue = webhook_test_client
        job_queue.enqueue_job.return_value = "msg-123"

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

        job_queue.enqueue_job.assert_awaited_once()
        enqueued_job = job_queue.enqueue_job.call_args.args[0]
        assert enqueued_job.user_description == "facepalm"
        assert enqueued_job.image_provider == "openai"

    def test_view_submission_enqueues_job_with_otel_trace_id_when_enabled(
        self, webhook_app_module, monkeypatch
    ):
        monkeypatch.setenv("TRACING_ENABLED", "true")
        monkeypatch.setenv("TRACE_SAMPLE_RATE", "1.0")
        monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)

        slack_repo = AsyncMock(spec=SlackModalRepository)
        job_queue = AsyncMock(spec=JobQueueProducer)

        security_service = MagicMock(spec=WebhookSecurityService)
        security_service.is_authentic_webhook.return_value = True

        processor = WebhookEventProcessor(
            slack_repo=slack_repo,
            job_queue=job_queue,
            google_enabled=True,
        )
        handler = SlackWebhookHandler(
            security_service=security_service,
            event_processor=processor,
        )

        app = webhook_app_module.create_app(webhook_handler=handler)
        client = TestClient(app)

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
        job_queue.enqueue_job.assert_awaited_once()
        enqueued_job = job_queue.enqueue_job.call_args.args[0]
        assert re.fullmatch(r"[0-9a-f]{32}", enqueued_job.trace_id)
