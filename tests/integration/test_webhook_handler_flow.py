import hashlib
import hmac
import json
import time
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from emojismith.application.handlers.slack_webhook_handler import (
    SlackWebhookHandler,
    WebhookEventProcessor,
)
from emojismith.domain.services.webhook_security_service import WebhookSecurityService
from emojismith.infrastructure.security.slack_signature_validator import (
    SlackSignatureValidator,
)
from emojismith.presentation.web.slack_webhook_api import create_webhook_api
from shared.domain.repositories import JobQueueProducer, SlackModalRepository


def _sign(body: bytes, secret: bytes, timestamp: str) -> str:
    """Create Slack-style signature for testing."""
    basestring = b"v0:" + timestamp.encode() + b":" + body
    digest = hmac.new(secret, basestring, hashlib.sha256).hexdigest()
    return "v0=" + digest


@pytest.fixture()
def app_with_mocks() -> tuple[TestClient, AsyncMock, AsyncMock, bytes]:
    secret = b"test_secret"
    slack_repo = AsyncMock(spec=SlackModalRepository)
    job_queue = AsyncMock(spec=JobQueueProducer)
    security_service = WebhookSecurityService(
        SlackSignatureValidator(signing_secret=secret)
    )
    processor = WebhookEventProcessor(slack_repo, job_queue)
    handler = SlackWebhookHandler(security_service, processor)
    app = create_webhook_api(handler)
    client = TestClient(app, raise_server_exceptions=False)
    return client, slack_repo, job_queue, secret


def _message_action_payload() -> dict:
    return {
        "type": "message_action",
        "callback_id": "create_emoji_reaction",
        "trigger_id": "TRIGGER",
        "user": {"id": "U123", "name": "tester"},
        "channel": {"id": "C1", "name": "general"},
        "message": {"text": "hello", "ts": "111.222", "user": "U999"},
        "team": {"id": "T1"},
    }


def _modal_payload() -> dict:
    return {
        "type": "view_submission",
        "view": {
            "callback_id": "emoji_creation_modal",
            "state": {
                "values": {
                    "emoji_name": {"name": {"value": "facepalm"}},
                    "emoji_description": {"description": {"value": "facepalm"}},
                    "share_location": {
                        "share_location_select": {
                            "selected_option": {"value": "channel"}
                        }
                    },
                    "instruction_visibility": {
                        "visibility_select": {"selected_option": {"value": "everyone"}}
                    },
                    "image_size": {
                        "size_select": {"selected_option": {"value": "emoji_size"}}
                    },
                    "style_preferences": {
                        "style_select": {"selected_option": {"value": "cartoon"}},
                        "detail_select": {"selected_option": {"value": "simple"}},
                    },
                    "color_scheme": {
                        "color_select": {"selected_option": {"value": "auto"}}
                    },
                    "tone": {"tone_select": {"selected_option": {"value": "fun"}}},
                }
            },
            "private_metadata": json.dumps(
                {
                    "message_text": "hello",
                    "user_id": "U123",
                    "channel_id": "C1",
                    "timestamp": "111.222",
                    "team_id": "T1",
                }
            ),
        },
    }


def _headers(body: bytes, secret: bytes) -> dict:
    ts = str(int(time.time()))
    return {
        "x-slack-request-timestamp": ts,
        "x-slack-signature": _sign(body, secret, ts),
        "Content-Type": "application/json",
    }


def test_complete_webhook_flow(
    app_with_mocks: tuple[TestClient, AsyncMock, AsyncMock, bytes],
) -> None:
    client, slack_repo, job_queue, secret = app_with_mocks
    # Step 1: message action
    body = json.dumps(_message_action_payload()).encode()
    resp = client.post("/slack/events", content=body, headers=_headers(body, secret))
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
    slack_repo.open_modal.assert_awaited_once()

    # Step 2: modal submission
    body2 = json.dumps(_modal_payload()).encode()
    resp2 = client.post("/slack/events", content=body2, headers=_headers(body2, secret))
    assert resp2.status_code == 200
    assert resp2.json() == {"response_action": "clear"}
    job_queue.enqueue_job.assert_awaited_once()
    job = job_queue.enqueue_job.call_args.args[0]
    assert job.user_description == "facepalm"
    assert job.channel_id == "C1"


def test_invalid_signature_rejected(
    app_with_mocks: tuple[TestClient, AsyncMock, AsyncMock, bytes],
) -> None:
    client, slack_repo, job_queue, _secret = app_with_mocks
    body = json.dumps(_message_action_payload()).encode()
    ts = str(int(time.time()))
    headers = {
        "X-Slack-Request-Timestamp": ts,
        "X-Slack-Signature": "v0=invalid",
        "Content-Type": "application/json",
    }
    resp = client.post("/slack/events", content=body, headers=headers)
    assert resp.status_code == 500
    slack_repo.open_modal.assert_not_called()
    job_queue.enqueue_job.assert_not_called()
