"""Integration tests for dual Lambda architecture."""

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
from shared.domain.repositories import JobQueueProducer, SlackModalRepository


@pytest.mark.integration()
class TestDualLambdaIntegration:
    """Test integration between webhook and worker Lambdas."""

    @pytest.fixture()
    def mock_slack_repo(self):
        """Mock Slack repository."""
        return AsyncMock(spec=SlackModalRepository)

    @pytest.fixture()
    def secret(self) -> bytes:
        return b"test_secret"

    @pytest.fixture()
    def webhook_handler(self, mock_slack_repo, secret):
        """Create webhook handler with dependencies."""
        job_queue = AsyncMock(spec=JobQueueProducer)
        security_service = WebhookSecurityService(
            SlackSignatureValidator(signing_secret=secret)
        )
        processor = WebhookEventProcessor(mock_slack_repo, job_queue)
        return SlackWebhookHandler(security_service, processor)

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
    def message_action_payload(self) -> dict[str, Any]:
        """Sample message action payload."""
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
        """Sample modal submission payload."""
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

    async def test_webhook_to_worker_flow_integration(
        self,
        webhook_handler,
        mock_slack_repo,
        secret,
        message_action_payload,
        modal_submission_payload,
    ):
        """Test complete flow from webhook to worker processing."""
        # Step 1: Handle message action (webhook Lambda)
        mock_slack_repo.open_modal.return_value = None

        body = json.dumps(message_action_payload).encode()
        result = await webhook_handler.handle_event(body, self._headers(body, secret))

        # Verify webhook response
        assert result == {"status": "ok"}
        mock_slack_repo.open_modal.assert_awaited_once()

        # Step 2: modal submission
        body2 = json.dumps(modal_submission_payload).encode()
        result = await webhook_handler.handle_event(body2, self._headers(body2, secret))

        # Verify modal submission response
        assert result == {"response_action": "clear"}

    async def test_webhook_handles_invalid_payloads_gracefully(
        self, webhook_handler, mock_slack_repo, secret
    ):
        """Test webhook handles malformed payloads gracefully."""
        invalid_payload = {
            "type": "message_action",
            "callback_id": "create_emoji_reaction",
        }
        body = json.dumps(invalid_payload).encode()
        with pytest.raises(ValueError):
            await webhook_handler.handle_event(body, self._headers(body, secret))

    async def test_webhook_performance_requirements(
        self, webhook_handler, mock_slack_repo, secret, message_action_payload
    ):
        """Test webhook meets performance requirements."""
        import time

        mock_slack_repo.open_modal.return_value = None

        start_time = time.time()
        body = json.dumps(message_action_payload).encode()
        result = await webhook_handler.handle_event(body, self._headers(body, secret))
        execution_time = time.time() - start_time

        assert execution_time < 0.1
        assert result == {"status": "ok"}
