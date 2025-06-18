"""Integration tests for dual Lambda architecture."""

import json
import pytest
from unittest.mock import AsyncMock, patch
from typing import Dict, Any

from webhook.handler import WebhookHandler
from webhook.infrastructure.sqs_job_queue import SQSJobQueue
from webhook.infrastructure.slack_api import SlackAPIRepository


class TestDualLambdaIntegration:
    """Test integration between webhook and worker Lambdas."""

    @pytest.fixture
    def mock_slack_repo(self):
        """Mock Slack repository."""
        return AsyncMock(spec=SlackAPIRepository)

    @pytest.fixture
    def webhook_handler(self, mock_slack_repo):
        """Create webhook handler with dependencies."""
        # Patch boto3.client during job queue creation
        with patch(
            "webhook.infrastructure.sqs_job_queue.boto3.client"
        ) as mock_boto_client:
            mock_sqs_client = mock_boto_client.return_value
            job_queue = SQSJobQueue(
                queue_url="https://sqs.us-east-1.amazonaws.com/123456789012/test-queue"
            )
            # Store the mock client for later access
            job_queue._mock_sqs_client = mock_sqs_client
            return WebhookHandler(slack_repo=mock_slack_repo, job_queue=job_queue)

    @pytest.fixture
    def message_action_payload(self) -> Dict[str, Any]:
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

    @pytest.fixture
    def modal_submission_payload(self) -> Dict[str, Any]:
        """Sample modal submission payload."""
        return {
            "type": "view_submission",
            "view": {
                "callback_id": "emoji_creation_modal",
                "state": {
                    "values": {
                        "emoji_description": {"description": {"value": "facepalm"}},
                        "emoji_name": {"name": {"value": "facepalm"}},
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
        message_action_payload,
        modal_submission_payload,
    ):
        """Test complete flow from webhook to worker processing."""
        # Step 1: Handle message action (webhook Lambda)
        mock_slack_repo.open_modal.return_value = None

        result = await webhook_handler.handle_message_action(message_action_payload)

        # Verify webhook response
        assert result == {"status": "ok"}
        mock_slack_repo.open_modal.assert_called_once()

        # Step 2: Handle modal submission (webhook Lambda)
        # Setup mock SQS client for modal submission
        mock_sqs_client = webhook_handler._job_queue._mock_sqs_client
        mock_sqs_client.send_message.return_value = {"MessageId": "test-message-id"}

        result = await webhook_handler.handle_modal_submission(modal_submission_payload)

        # Verify modal submission response
        assert result == {"response_action": "clear"}

        # Verify SQS message was sent
        mock_sqs_client.send_message.assert_called_once()
        sqs_call_args = mock_sqs_client.send_message.call_args

        # Verify message body contains job data
        message_body = json.loads(sqs_call_args.kwargs["MessageBody"])
        assert message_body["user_description"] == "facepalm"
        assert message_body["message_text"] == "Just deployed on Friday"
        assert message_body["user_id"] == "U12345"
        assert message_body["sharing_preferences"]["share_location"] == "channel"

    async def test_webhook_handles_invalid_payloads_gracefully(
        self, webhook_handler, mock_slack_repo
    ):
        """Test webhook handles malformed payloads gracefully."""
        # Test invalid message action payload
        invalid_payload = {
            "type": "message_action",
            "callback_id": "create_emoji_reaction",
            # Missing required fields
        }

        with pytest.raises(ValueError, match="Invalid message action payload"):
            await webhook_handler.handle_message_action(invalid_payload)

        # Test invalid modal submission payload
        invalid_modal = {
            "type": "view_submission",
            "view": {
                "callback_id": "emoji_creation_modal",
                # Missing state
            },
        }

        with pytest.raises(ValueError, match="Invalid modal submission payload"):
            await webhook_handler.handle_modal_submission(invalid_modal)

    async def test_webhook_performance_requirements(
        self, webhook_handler, mock_slack_repo, message_action_payload
    ):
        """Test webhook meets performance requirements."""
        import time

        # Mock modal opening to be fast
        mock_slack_repo.open_modal.return_value = None

        # Measure execution time
        start_time = time.time()
        result = await webhook_handler.handle_message_action(message_action_payload)
        execution_time = time.time() - start_time

        # Verify fast response (should be well under 1 second)
        assert execution_time < 0.1  # 100ms threshold for unit test
        assert result == {"status": "ok"}

    async def test_sqs_message_format_compatibility(
        self, webhook_handler, modal_submission_payload
    ):
        """Test SQS message format is compatible with worker Lambda."""
        from shared.domain.entities import EmojiGenerationJob

        # Setup mock SQS client for modal submission
        mock_sqs_client = webhook_handler._job_queue._mock_sqs_client
        mock_sqs_client.send_message.return_value = {"MessageId": "test-message-id"}

        # Handle modal submission
        await webhook_handler.handle_modal_submission(modal_submission_payload)

        # Extract the message body that would be sent to SQS
        sqs_call_args = mock_sqs_client.send_message.call_args
        message_body = json.loads(sqs_call_args.kwargs["MessageBody"])

        # Verify worker Lambda can parse the message
        job = EmojiGenerationJob.from_dict(message_body)

        # Verify job data is correct
        assert job.user_description == "facepalm"
        assert job.message_text == "Just deployed on Friday"
        assert job.user_id == "U12345"
        assert job.channel_id == "C67890"
        assert job.sharing_preferences.share_location.value == "channel"
        assert job.sharing_preferences.instruction_visibility.value == "EVERYONE"
        assert job.sharing_preferences.image_size.value == "EMOJI_SIZE"
