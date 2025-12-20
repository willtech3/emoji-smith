"""End-to-end integration tests for dual Lambda architecture."""

import hashlib
import hmac
import json
import time
from typing import Any
from unittest.mock import AsyncMock

import pytest

from emojismith.application.handlers.slack_webhook_handler import (
    SlackWebhookHandler,
    WebhookEventProcessor,
)
from emojismith.domain.services.webhook_security_service import WebhookSecurityService
from emojismith.infrastructure.security.slack_signature_validator import (
    SlackSignatureValidator,
)
from shared.domain.entities import EmojiGenerationJob
from shared.domain.repositories import JobQueueProducer, SlackModalRepository


@pytest.mark.integration()
class TestDualLambdaE2EIntegration:
    """End-to-end integration tests for webhook to worker flow."""

    def _headers(self, body: bytes, secret: bytes) -> dict[str, str]:
        ts = str(int(time.time()))
        basestring = b"v0:" + ts.encode() + b":" + body
        sig = "v0=" + hmac.new(secret, basestring, hashlib.sha256).hexdigest()
        return {
            "x-slack-request-timestamp": ts,
            "x-slack-signature": sig,
            "Content-Type": "application/json",
        }

    @pytest.fixture()
    def mock_slack_repo(self):
        """Mock Slack repository with realistic responses."""
        mock_repo = AsyncMock(spec=SlackModalRepository)
        mock_repo.open_modal.return_value = None
        return mock_repo

    @pytest.fixture()
    def webhook_handler(self, mock_slack_repo):
        """Create webhook handler with mocked dependencies."""
        job_queue = AsyncMock(spec=JobQueueProducer)
        security_service = WebhookSecurityService(
            SlackSignatureValidator(signing_secret=b"test_secret")
        )
        processor = WebhookEventProcessor(mock_slack_repo, job_queue)
        return SlackWebhookHandler(security_service, processor)

    @pytest.fixture()
    def message_action_payload(self) -> dict[str, Any]:
        """Complete message action payload for testing."""
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
    def modal_submission_payload(self) -> dict[str, Any]:
        """Complete modal submission payload for testing."""
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
                        "message_text": "Just deployed on Friday",
                        "user_id": "U12345",
                        "channel_id": "C67890",
                        "timestamp": "1234567890.123456",
                        "team_id": "T11111",
                    }
                ),
            },
        }

    async def test_complete_webhook_to_sqs_flow_integration(
        self,
        webhook_handler,
        mock_slack_repo,
        message_action_payload,
        modal_submission_payload,
    ):
        """Test complete flow: webhook → SQS → worker-ready message."""
        # Step 1: Handle message action (should open modal immediately)
        body = json.dumps(message_action_payload).encode()
        result = await webhook_handler.handle_event(
            body, self._headers(body, b"test_secret")
        )

        assert result == {"status": "ok"}
        mock_slack_repo.open_modal.assert_called_once()

        # Step 2: Handle modal submission (should queue job)
        body2 = json.dumps(modal_submission_payload).encode()
        result = await webhook_handler.handle_event(
            body2, self._headers(body2, b"test_secret")
        )

        assert result == {"response_action": "clear"}

    async def test_webhook_performance_timing(
        self,
        webhook_handler,
        modal_submission_payload,
    ):
        """Test webhook meets performance requirements."""
        import time

        start_time = time.time()
        body = json.dumps(modal_submission_payload).encode()
        result = await webhook_handler.handle_event(
            body, self._headers(body, b"test_secret")
        )
        end_time = time.time()

        assert end_time - start_time < 1.0
        assert result == {"response_action": "clear"}

    async def test_worker_lambda_compatibility(
        self,
        modal_submission_payload,
    ):
        """Ensure worker-compatible payload structure via domain round-trip."""
        message_body = {
            "job_id": "id",
            "user_description": "facepalm",
            "message_text": "Just deployed on Friday",
            "user_id": "U12345",
            "channel_id": "C67890",
            "team_id": "T11111",
            "timestamp": "1234567890.123456",
            "emoji_name": "facepalm",
            "status": "PENDING",
            "sharing_preferences": {
                "share_location": "channel",
                "instruction_visibility": "EVERYONE",
                "image_size": "EMOJI_SIZE",
            },
            "style_preferences": {},
            "thread_ts": None,
            "created_at": "2025-08-09T00:00:00+00:00",
        }
        job = EmojiGenerationJob.from_dict(message_body)
        assert job.to_dict()["user_description"] == "facepalm"
