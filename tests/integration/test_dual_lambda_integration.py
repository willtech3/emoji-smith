"""Integration tests for dual Lambda architecture."""

import json
from typing import Any, Dict, Tuple

import boto3
import pytest
from moto import mock_aws
from unittest.mock import AsyncMock

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
    def sqs_setup(self) -> Tuple[boto3.client, str]:
        """Create an SQS queue using moto."""
        with mock_aws():
            boto3.setup_default_session(region_name="us-east-1")
            sqs = boto3.client("sqs")
            queue_url = sqs.create_queue(QueueName="test-queue")["QueueUrl"]
            yield sqs, queue_url

    @pytest.fixture
    def webhook_handler(self, mock_slack_repo, sqs_setup):
        """Create webhook handler with moto-backed SQS."""
        _, queue_url = sqs_setup
        job_queue = SQSJobQueue(queue_url=queue_url)
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

    async def test_webhook_to_worker_flow_integration(
        self,
        webhook_handler,
        mock_slack_repo,
        message_action_payload,
        modal_submission_payload,
        sqs_setup,
    ):
        """Test complete flow from webhook to worker processing."""
        # Step 1: Handle message action (webhook Lambda)
        mock_slack_repo.open_modal.return_value = None

        result = await webhook_handler.handle_message_action(message_action_payload)

        # Verify webhook response
        assert result == {"status": "ok"}
        mock_slack_repo.open_modal.assert_called_once()

        # Step 2: Handle modal submission (webhook Lambda)
        _, queue_url = sqs_setup
        result = await webhook_handler.handle_modal_submission(modal_submission_payload)

        # Verify modal submission response
        assert result == {"response_action": "clear"}

        sqs_client, _ = sqs_setup
        messages = sqs_client.receive_message(QueueUrl=queue_url, MaxNumberOfMessages=1)
        message_body = json.loads(messages["Messages"][0]["Body"])
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
        self,
        webhook_handler,
        modal_submission_payload,
        sqs_setup,
    ):
        """Test SQS message format is compatible with worker Lambda."""
        from shared.domain.entities import EmojiGenerationJob

        # Handle modal submission
        sqs_client, queue_url = sqs_setup
        await webhook_handler.handle_modal_submission(modal_submission_payload)

        messages = sqs_client.receive_message(QueueUrl=queue_url, MaxNumberOfMessages=1)
        message_body = json.loads(messages["Messages"][0]["Body"])

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
