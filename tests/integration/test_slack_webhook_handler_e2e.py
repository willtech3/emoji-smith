import json
import time
import hmac
import hashlib
from typing import Dict, Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from webhook.handler import WebhookHandler
from webhook.infrastructure.sqs_job_queue import SQSJobQueue
from webhook.infrastructure.slack_api import SlackAPIRepository
from webhook.infrastructure.slack_signature_validator import SlackSignatureValidator
from webhook.security.webhook_security_service import WebhookSecurityService

from emojismith.application.handlers.slack_webhook_handler import (
    SlackWebhookHandler,
    WebhookEventProcessor,
    UnauthorizedError,
)


@pytest.fixture
def signing_secret() -> bytes:
    return b"test_secret"


@pytest.fixture
def security_service(signing_secret: bytes) -> WebhookSecurityService:
    validator = SlackSignatureValidator(signing_secret=signing_secret)
    return WebhookSecurityService(validator)


@pytest.fixture
def mock_slack_repo() -> AsyncMock:
    repo = AsyncMock(spec=SlackAPIRepository)
    repo.open_modal.return_value = None
    return repo


@pytest.fixture
def sqs_client() -> MagicMock:
    client = MagicMock()
    client.send_message.return_value = {"MessageId": "msg"}
    return client


@pytest.fixture
def slack_handler(
    security_service: WebhookSecurityService,
    mock_slack_repo: AsyncMock,
    sqs_client: MagicMock,
) -> SlackWebhookHandler:
    with patch("webhook.infrastructure.sqs_job_queue.boto3.client") as mock_boto:
        mock_boto.return_value = sqs_client
        job_queue = SQSJobQueue(queue_url="https://sqs.example.com/queue")
        webhook = WebhookHandler(slack_repo=mock_slack_repo, job_queue=job_queue)
    processor = WebhookEventProcessor(webhook)
    return SlackWebhookHandler(security_service, processor)


def _signed_headers(body: bytes, secret: bytes) -> Dict[str, str]:
    timestamp = str(int(time.time()))
    sig_basestring = b"v0:" + timestamp.encode() + b":" + body
    signature = "v0=" + hmac.new(secret, sig_basestring, hashlib.sha256).hexdigest()
    return {
        "X-Slack-Request-Timestamp": timestamp,
        "X-Slack-Signature": signature,
    }


@pytest.fixture
def message_action_payload() -> Dict[str, Any]:
    return {
        "type": "message_action",
        "callback_id": "create_emoji_reaction",
        "trigger_id": "123456789.987654321.abcdefghijklmnopqrstuvwxyz",
        "user": {"id": "U12345", "name": "testuser"},
        "channel": {"id": "C67890", "name": "general"},
        "message": {
            "text": "Just deployed on Friday afternoon!",
            "ts": "1234567890.123456",
            "user": "U98765",
        },
        "team": {"id": "T11111"},
    }


@pytest.fixture
def modal_submission_payload() -> Dict[str, Any]:
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
                    "message_text": "Just deployed on Friday",
                    "user_id": "U12345",
                    "channel_id": "C67890",
                    "timestamp": "1234567890.123456",
                    "team_id": "T11111",
                }
            ),
        },
    }


@pytest.mark.asyncio
async def test_complete_webhook_flow(
    slack_handler: SlackWebhookHandler,
    mock_slack_repo: AsyncMock,
    sqs_client: MagicMock,
    signing_secret: bytes,
    message_action_payload: Dict[str, Any],
    modal_submission_payload: Dict[str, Any],
) -> None:
    body = json.dumps(message_action_payload).encode()
    headers = _signed_headers(body, signing_secret)

    result = await slack_handler.handle_event(body, headers)

    assert result == {"status": "ok"}
    mock_slack_repo.open_modal.assert_called_once()

    body2 = json.dumps(modal_submission_payload).encode()
    headers2 = _signed_headers(body2, signing_secret)

    result2 = await slack_handler.handle_event(body2, headers2)

    assert result2 == {"response_action": "clear"}
    sqs_client.send_message.assert_called_once()
    message_body = json.loads(sqs_client.send_message.call_args.kwargs["MessageBody"])
    assert message_body["emoji_name"] == "facepalm"
    assert message_body["user_description"] == "facepalm"


@pytest.mark.asyncio
async def test_invalid_signature_raises(
    slack_handler: SlackWebhookHandler,
    message_action_payload: Dict[str, Any],
    signing_secret: bytes,
) -> None:
    body = json.dumps(message_action_payload).encode()
    headers = _signed_headers(body, signing_secret)
    headers["X-Slack-Signature"] = "v0=invalid"

    with pytest.raises(UnauthorizedError):
        await slack_handler.handle_event(body, headers)
