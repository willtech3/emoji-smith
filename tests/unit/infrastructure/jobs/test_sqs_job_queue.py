"""Tests for SQS job queue implementation."""

import json
import pytest
from unittest.mock import AsyncMock, Mock
from emojismith.infrastructure.jobs.sqs_job_queue import SQSJobQueue


class TestSQSJobQueue:
    """Test SQS job queue implementation."""

    @pytest.fixture
    def mock_sqs_client(self):
        """Mock SQS client."""
        return AsyncMock()

    @pytest.fixture
    def mock_session(self, mock_sqs_client):
        """Mock aioboto3 session that returns mocked SQS client."""
        session = Mock()
        # Create an async context manager for the client
        async_context_manager = AsyncMock()
        async_context_manager.__aenter__.return_value = mock_sqs_client
        async_context_manager.__aexit__.return_value = None
        session.client.return_value = async_context_manager
        return session

    @pytest.fixture
    def sqs_queue(self, mock_session):
        """SQS job queue with mocked session."""
        return SQSJobQueue(
            session=mock_session,
            queue_url="https://sqs.us-east-1.amazonaws.com/123456789/emoji-jobs",
        )

    async def test_queues_emoji_generation_for_background_processing(
        self, sqs_queue, mock_sqs_client
    ):
        """Test enqueuing job sends job directly to SQS."""
        # Arrange
        from shared.domain.entities import EmojiGenerationJob

        from shared.domain.value_objects import EmojiSharingPreferences

        job = EmojiGenerationJob.create_new(
            message_text="Just deployed on Friday!",
            user_description="facepalm reaction",
            user_id="U12345",
            channel_id="C67890",
            timestamp="1234567890.123456",
            team_id="T11111",
            sharing_preferences=EmojiSharingPreferences.default_for_context(),
        )
        mock_sqs_client.send_message.return_value = {
            "MessageId": "msg_123",
            "MD5OfBody": "abc123",
        }

        # Act
        job_id = await sqs_queue.enqueue_job(job)

        # Assert
        assert job_id == job.job_id
        assert mock_sqs_client.send_message.called
        call_args = mock_sqs_client.send_message.call_args
        assert call_args.kwargs["QueueUrl"] == sqs_queue.queue_url

        # Verify message contains job data directly
        message_body = call_args.kwargs["MessageBody"]
        import json

        message_data = json.loads(message_body)
        assert message_data["job_id"] == job.job_id
        assert message_data["message_text"] == "Just deployed on Friday!"

        # Verify FIFO parameters are not sent for standard queue
        assert "MessageGroupId" not in call_args.kwargs
        assert "MessageDeduplicationId" not in call_args.kwargs

    async def test_retrieves_next_emoji_job_for_processing(
        self, sqs_queue, mock_sqs_client
    ):
        """Test dequeuing job receives job data directly from SQS."""
        # Arrange
        job_message = {
            "job_id": "job_123",
            "message_text": "test message",
            "user_description": "test emoji",
            "user_id": "U12345",
            "channel_id": "C67890",
            "timestamp": "123.456",
            "team_id": "T11111",
            "status": "PENDING",
            "created_at": "2023-01-01T12:00:00+00:00",
            "sharing_preferences": {
                "share_location": "channel",
                "instruction_visibility": "EVERYONE",
                "include_upload_instructions": True,
                "image_size": "EMOJI_SIZE",
                "thread_ts": None,
            },
        }

        mock_sqs_client.receive_message.return_value = {
            "Messages": [
                {
                    "MessageId": "msg_123",
                    "ReceiptHandle": "receipt_123",
                    "Body": json.dumps(job_message),
                }
            ]
        }

        # Act
        result = await sqs_queue.dequeue_job()

        # Assert
        assert mock_sqs_client.receive_message.called
        assert result is not None
        job, receipt_handle = result
        assert job.job_id == "job_123"
        assert receipt_handle == "receipt_123"

    async def test_removes_completed_job_from_queue(self, sqs_queue, mock_sqs_client):
        """Test complete_job calls delete_message when receipt_handle is present."""
        # Arrange: create dummy job with receipt_handle
        from shared.domain.entities import EmojiGenerationJob

        from shared.domain.value_objects import EmojiSharingPreferences

        job = EmojiGenerationJob.create_new(
            message_text="x",
            user_description="y",
            user_id="U1",
            channel_id="C1",
            timestamp="ts",
            team_id="T1",
            sharing_preferences=EmojiSharingPreferences.default_for_context(),
        )
        receipt_handle = "rh"

        # Act
        await sqs_queue.complete_job(job, receipt_handle)

        # Assert
        mock_sqs_client.delete_message.assert_called_with(
            QueueUrl=sqs_queue.queue_url, ReceiptHandle="rh"
        )

    async def test_provides_job_status_tracking_methods(self, sqs_queue):
        """get_job_status, update_job_status, retry_failed_jobs no-ops or defaults."""
        status = await sqs_queue.get_job_status("jid")
        assert status is None

        # update_job_status should not error
        await sqs_queue.update_job_status("jid", "processing")

        # retry_failed_jobs returns 0
        count = await sqs_queue.retry_failed_jobs(max_retries=5)
        assert count == 0

    async def test_handles_corrupted_job_data_gracefully(
        self, sqs_queue, mock_sqs_client
    ):
        """Malformed JSON body triggers deletion and returns None."""
        malformed = {"Messages": [{"ReceiptHandle": "rh", "Body": "not a json"}]}
        mock_sqs_client.receive_message.return_value = malformed

        result = await sqs_queue.dequeue_job()
        assert result is None
        mock_sqs_client.delete_message.assert_called_with(
            QueueUrl=sqs_queue.queue_url, ReceiptHandle="rh"
        )
