import json
import hmac
import hashlib
import time
from typing import Dict, Any
from fastapi.testclient import TestClient
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from webhook.handler import WebhookHandler
from webhook.infrastructure.slack_api import SlackAPIRepository
from webhook.infrastructure.sqs_job_queue import SQSJobQueue
from shared.domain.entities import EmojiGenerationJob
from webhook.infrastructure.slack_signature_validator import SlackSignatureValidator
from webhook.security.webhook_security_service import WebhookSecurityService
from emojismith.application.handlers.slack_webhook_handler import (
    SlackWebhookHandler,
    WebhookEventProcessor,
)
from emojismith.presentation.web.slack_webhook_api import create_webhook_api


class TestSlackWebhookHandlerE2E:
    """End-to-end tests for SlackWebhookHandler with signature validation."""

    SIGNING_SECRET = "test_signing_secret"

    @staticmethod
    def _generate_signature(body: bytes, timestamp: str) -> str:
        basestring = b"v0:" + timestamp.encode() + b":" + body
        digest = hmac.new(
            TestSlackWebhookHandlerE2E.SIGNING_SECRET.encode(),
            basestring,
            hashlib.sha256,
        ).hexdigest()
        return "v0=" + digest

    @pytest.fixture()
    def security_service(self) -> WebhookSecurityService:
        validator = SlackSignatureValidator(signing_secret=self.SIGNING_SECRET.encode())
        return WebhookSecurityService(validator)

    @pytest.fixture()
    def mock_slack_repo(self):
        repo = AsyncMock(spec=SlackAPIRepository)
        repo.open_modal.return_value = None
        return repo

    @pytest.fixture()
    def mock_sqs_client(self):
        client = MagicMock()
        client.send_message.return_value = {"MessageId": "msg-123"}
        return client

    @pytest.fixture()
    def slack_app(self, security_service, mock_slack_repo, mock_sqs_client):
        with patch("webhook.infrastructure.sqs_job_queue.boto3.client") as mock_boto:
            mock_boto.return_value = mock_sqs_client
            job_queue = SQSJobQueue(
                queue_url="https://sqs.us-east-1.amazonaws.com/123/test"
            )
            webhook_handler = WebhookHandler(
                slack_repo=mock_slack_repo, job_queue=job_queue
            )
            webhook_handler._sqs_client = mock_sqs_client
            processor = WebhookEventProcessor(webhook_handler)
            handler = SlackWebhookHandler(security_service, processor)
            app = create_webhook_api(handler)
            return TestClient(app, raise_server_exceptions=False)

    @pytest.fixture()
    def message_action_payload(self) -> Dict[str, Any]:
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

    @pytest.fixture()
    def modal_submission_payload(self) -> Dict[str, Any]:
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
                            "visibility_select": {
                                "selected_option": {"value": "everyone"}
                            }
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

    def test_full_flow_with_valid_signatures(
        self,
        slack_app: TestClient,
        mock_slack_repo: AsyncMock,
        mock_sqs_client: MagicMock,
        message_action_payload: Dict[str, Any],
        modal_submission_payload: Dict[str, Any],
    ) -> None:
        timestamp = str(int(time.time()))
        body = json.dumps(message_action_payload).encode()
        signature = self._generate_signature(body, timestamp)
        headers = {
            "x-slack-request-timestamp": timestamp,
            "x-slack-signature": signature,
            "content-type": "application/json",
        }

        resp = slack_app.post("/slack/events", content=body, headers=headers)
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}
        mock_slack_repo.open_modal.assert_awaited_once()

        timestamp2 = str(int(time.time()))
        body2 = json.dumps(modal_submission_payload).encode()
        signature2 = self._generate_signature(body2, timestamp2)
        headers2 = {
            "x-slack-request-timestamp": timestamp2,
            "x-slack-signature": signature2,
            "content-type": "application/json",
        }

        resp2 = slack_app.post("/slack/events", content=body2, headers=headers2)
        assert resp2.status_code == 200
        assert resp2.json() == {"response_action": "clear"}

        mock_sqs_client.send_message.assert_called_once()
        send_call = mock_sqs_client.send_message.call_args
        message_body = json.loads(send_call.kwargs["MessageBody"])
        job = EmojiGenerationJob.from_dict(message_body)
        assert job.user_description == "facepalm"
        assert job.message_text == "Just deployed on Friday"
        assert job.user_id == "U12345"
        assert job.channel_id == "C67890"
        assert job.team_id == "T11111"
        assert job.timestamp == "1234567890.123456"

    def test_invalid_signature_returns_error(
        self,
        slack_app: TestClient,
        message_action_payload: Dict[str, Any],
    ) -> None:
        timestamp = str(int(time.time()))
        body = json.dumps(message_action_payload).encode()
        headers = {
            "x-slack-request-timestamp": timestamp,
            "x-slack-signature": "v0=invalid",
            "content-type": "application/json",
        }
        resp = slack_app.post("/slack/events", content=body, headers=headers)
        assert resp.status_code == 500
