"""End-to-end integration tests for dual Lambda architecture."""

import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from typing import Dict, Any

from webhook.handler import WebhookHandler
from webhook.infrastructure.slack_api import SlackAPIRepository
from webhook.infrastructure.sqs_job_queue import SQSJobQueue
from shared.domain.entities import EmojiGenerationJob


class TestDualLambdaE2EIntegration:
    """End-to-end integration tests for webhook to worker flow."""

    @pytest.fixture
    def mock_slack_repo(self):
        """Mock Slack repository with realistic responses."""
        mock_repo = AsyncMock(spec=SlackAPIRepository)
        mock_repo.open_modal.return_value = None
        return mock_repo

    @pytest.fixture
    def mock_sqs_client(self):
        """Mock SQS client that captures sent messages."""
        mock_client = MagicMock()
        mock_client.send_message.return_value = {"MessageId": "test-message-id"}
        return mock_client

    @pytest.fixture
    def webhook_handler(self, mock_slack_repo, mock_sqs_client):
        """Create webhook handler with mocked dependencies."""
        # Create job queue with mocked SQS client
        with patch("webhook.infrastructure.sqs_job_queue.boto3.client") as mock_boto:
            mock_boto.return_value = mock_sqs_client
            job_queue = SQSJobQueue(
                queue_url="https://sqs.us-east-1.amazonaws.com/123456789012/test-queue"
            )

            webhook_handler = WebhookHandler(
                slack_repo=mock_slack_repo, job_queue=job_queue
            )
            # Attach mock client for verification
            webhook_handler._sqs_client = mock_sqs_client
            return webhook_handler

    @pytest.fixture
    def message_action_payload(self) -> Dict[str, Any]:
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

    @pytest.fixture
    def modal_submission_payload(self) -> Dict[str, Any]:
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

    async def test_complete_webhook_to_sqs_flow_integration(
        self,
        webhook_handler,
        mock_slack_repo,
        mock_sqs_client,
        message_action_payload,
        modal_submission_payload,
    ):
        """Test complete flow: webhook → SQS → worker-ready message."""
        # Step 1: Handle message action (should open modal immediately)
        result = await webhook_handler.handle_message_action(message_action_payload)

        # Verify webhook response is immediate
        assert result == {"status": "ok"}
        mock_slack_repo.open_modal.assert_called_once()

        # Verify modal was opened with correct trigger_id
        modal_call = mock_slack_repo.open_modal.call_args
        assert (
            modal_call.kwargs["trigger_id"]
            == "123456789.987654321.abcdefghijklmnopqrstuvwxyz"
        )

        # Step 2: Handle modal submission (should queue job to SQS)
        result = await webhook_handler.handle_modal_submission(modal_submission_payload)

        # Verify modal submission response
        assert result == {"response_action": "clear"}

        # Step 3: Verify SQS message was sent
        mock_sqs_client.send_message.assert_called_once()

        # Get the message that was sent to SQS
        send_call = mock_sqs_client.send_message.call_args
        assert (
            send_call.kwargs["QueueUrl"]
            == "https://sqs.us-east-1.amazonaws.com/123456789012/test-queue"
        )

        message_body = json.loads(send_call.kwargs["MessageBody"])

        # Step 4: Verify message format is compatible with worker Lambda
        # Worker Lambda should be able to parse this into EmojiGenerationJob
        job = EmojiGenerationJob.from_dict(message_body)

        # Verify job data is correct
        assert job.user_description == "facepalm"
        assert job.message_text == "Just deployed on Friday"
        assert job.user_id == "U12345"
        assert job.channel_id == "C67890"
        assert job.team_id == "T11111"
        assert job.timestamp == "1234567890.123456"
        assert job.sharing_preferences.share_location.value == "channel"
        assert job.sharing_preferences.instruction_visibility.value == "EVERYONE"
        assert job.sharing_preferences.image_size.value == "EMOJI_SIZE"

        # Verify job has required worker fields
        assert job.job_id is not None
        assert job.created_at is not None

    async def test_webhook_performance_timing(
        self, webhook_handler, mock_sqs_client, modal_submission_payload,
    ):
        """Test webhook meets performance requirements."""
        import time

        # Measure timing
        start_time = time.time()
        result = await webhook_handler.handle_modal_submission(modal_submission_payload)
        end_time = time.time()

        # Verify fast response (webhook requirement)
        assert end_time - start_time < 1.0  # Should complete in under 1 second
        assert result == {"response_action": "clear"}

        # Verify SQS message was sent
        mock_sqs_client.send_message.assert_called_once()

        # Get the message that was sent to SQS
        send_call = mock_sqs_client.send_message.call_args
        message_body = json.loads(send_call.kwargs["MessageBody"])

        # Essential fields for worker Lambda
        required_fields = [
            "job_id",
            "user_description",
            "message_text",
            "user_id",
            "channel_id",
            "team_id",
            "timestamp",
            "emoji_name",
            "sharing_preferences",
        ]

        for field in required_fields:
            assert field in message_body, f"Missing required field: {field}"

        # Verify sharing preferences structure
        sharing_prefs = message_body["sharing_preferences"]
        assert "share_location" in sharing_prefs
        assert "instruction_visibility" in sharing_prefs
        assert "image_size" in sharing_prefs

    async def test_error_handling_no_sqs_on_failure(
        self, webhook_handler, mock_sqs_client,
    ):
        """Test error handling - no SQS messages sent on failure."""
        # Test with invalid modal payload
        invalid_payload = {
            "type": "view_submission",
            "view": {
                "callback_id": "emoji_creation_modal",
                # Missing required fields
            },
        }

        with pytest.raises(ValueError, match="Invalid modal submission payload"):
            await webhook_handler.handle_modal_submission(invalid_payload)

        # Verify no messages were sent to SQS on error
        mock_sqs_client.send_message.assert_not_called()

    async def test_worker_lambda_compatibility(
        self, webhook_handler, mock_sqs_client, modal_submission_payload,
    ):
        """Test that messages are fully compatible with worker Lambda."""
        # Send message through webhook
        result = await webhook_handler.handle_modal_submission(modal_submission_payload)
        assert result == {"response_action": "clear"}

        # Get the message that was sent to SQS
        send_call = mock_sqs_client.send_message.call_args
        message_body = json.loads(send_call.kwargs["MessageBody"])

        # Verify worker Lambda can parse the message without errors
        job = EmojiGenerationJob.from_dict(message_body)

        # Verify job can be serialized back to dict (round-trip test)
        job_dict = job.to_dict()

        # Verify essential fields are preserved
        assert job_dict["user_description"] == job.user_description
        assert job_dict["message_text"] == job.message_text
        assert job_dict["user_id"] == job.user_id
        assert (
            job_dict["sharing_preferences"]["share_location"]
            == job.sharing_preferences.share_location.value
        )

        # Verify job can be recreated from dict
        job_recreated = EmojiGenerationJob.from_dict(job_dict)
        assert job_recreated.user_description == job.user_description
        assert job_recreated.job_id == job.job_id
