"""Tests for SQS job queue implementation."""

import pytest
from unittest.mock import AsyncMock
from emojismith.infrastructure.jobs.sqs_job_queue import SQSJobQueue


class TestSQSJobQueue:
    """Test SQS job queue implementation."""

    @pytest.fixture
    def mock_sqs_client(self):
        """Mock SQS client."""
        return AsyncMock()

    @pytest.fixture
    def sqs_queue(self, mock_sqs_client):
        """SQS job queue with mocked client."""
        return SQSJobQueue(
            sqs_client=mock_sqs_client,
            queue_url="https://sqs.us-east-1.amazonaws.com/123456789/emoji-jobs",
        )

    async def test_enqueue_job_sends_message_to_sqs(self, sqs_queue, mock_sqs_client):
        """Test enqueuing job sends message to SQS."""
        # Arrange
        job_data = {
            "message_text": "Just deployed on Friday!",
            "user_description": "facepalm reaction",
            "user_id": "U12345",
            "channel_id": "C67890",
            "timestamp": "1234567890.123456",
            "team_id": "T11111",
        }
        mock_sqs_client.send_message.return_value = {
            "MessageId": "msg_123",
            "MD5OfBody": "abc123",
        }

        # Act
        job_id = await sqs_queue.enqueue_job(job_data)

        # Assert
        assert job_id is not None
        mock_sqs_client.send_message.assert_called_once()
        call_args = mock_sqs_client.send_message.call_args
        assert call_args[1]["QueueUrl"] == sqs_queue._queue_url
        assert "MessageBody" in call_args[1]

    async def test_dequeue_job_receives_message_from_sqs(
        self, sqs_queue, mock_sqs_client
    ):
        """Test dequeuing job receives message from SQS."""
        # Arrange
        job_data = {
            "job_id": "job_123",
            "message_text": "test message",
            "user_description": "test emoji",
            "user_id": "U12345",
            "channel_id": "C67890",
            "timestamp": "123.456",
            "team_id": "T11111",
            "status": "pending",
            "created_at": "2023-01-01T12:00:00+00:00",
        }

        mock_sqs_client.receive_message.return_value = {
            "Messages": [
                {
                    "MessageId": "msg_123",
                    "ReceiptHandle": "receipt_123",
                    "Body": str(job_data).replace("'", '"'),  # JSON-like format
                }
            ]
        }

        # Act
        job = await sqs_queue.dequeue_job()

        # Assert
        mock_sqs_client.receive_message.assert_called_once()
        assert job is not None
        assert job.job_id == "job_123"
