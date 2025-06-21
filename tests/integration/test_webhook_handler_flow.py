import json
import time
import hmac
import hashlib
from typing import Tuple

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch

from emojismith.presentation.web.slack_webhook_api import create_webhook_api
from emojismith.application.handlers.slack_webhook_handler import (
    SlackWebhookHandler,
    WebhookEventProcessor,
)
from webhook.handler import WebhookHandler
from webhook.infrastructure.slack_signature_validator import SlackSignatureValidator
from webhook.security.webhook_security_service import WebhookSecurityService
from webhook.infrastructure.sqs_job_queue import SQSJobQueue
from shared.domain.repositories import SlackModalRepository


def _sign(body: bytes, secret: bytes, timestamp: str) -> str:
    """Create Slack-style signature for testing."""
    basestring = b"v0:" + timestamp.encode() + b":" + body
    digest = hmac.new(secret, basestring, hashlib.sha256).hexdigest()
    return "v0=" + digest


@pytest.fixture
def app_with_mocks() -> Tuple[TestClient, AsyncMock, MagicMock, bytes]:
    secret = b"test_secret"
    slack_repo = AsyncMock(spec=SlackModalRepository)
    sqs_client = MagicMock()
    sqs_client.send_message.return_value = {"MessageId": "test"}
    with patch(
        "webhook.infrastructure.sqs_job_queue.boto3.client", return_value=sqs_client
    ):
        job_queue = SQSJobQueue("https://sqs.example.com/test")
        webhook_handler = WebhookHandler(slack_repo, job_queue)
        security_service = WebhookSecurityService(
            SlackSignatureValidator(signing_secret=secret)
        )
        processor = WebhookEventProcessor(webhook_handler)
        handler = SlackWebhookHandler(security_service, processor)
        app = create_webhook_api(handler)
        client = TestClient(app, raise_server_exceptions=False)
        yield client, slack_repo, sqs_client, secret


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
                    "style_type": {
                        "style_select": {"selected_option": {"value": "cartoon"}}
                    },
                    "color_scheme": {
                        "color_select": {"selected_option": {"value": "auto"}}
                    },
                    "detail_level": {
                        "detail_select": {"selected_option": {"value": "simple"}}
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
    app_with_mocks: Tuple[TestClient, AsyncMock, MagicMock, bytes],
) -> None:
    client, slack_repo, sqs_client, secret = app_with_mocks
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
    sqs_client.send_message.assert_called_once()
    msg = json.loads(sqs_client.send_message.call_args.kwargs["MessageBody"])
    assert msg["user_description"] == "facepalm"
    assert msg["channel_id"] == "C1"


def test_invalid_signature_rejected(
    app_with_mocks: Tuple[TestClient, AsyncMock, MagicMock, bytes],
) -> None:
    client, slack_repo, sqs_client, secret = app_with_mocks
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
    sqs_client.send_message.assert_not_called()
