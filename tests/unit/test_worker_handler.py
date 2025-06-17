"""Unit tests for SQS worker handler."""

import json
import os
import pytest
from unittest.mock import Mock, patch
from typing import Dict, Any

from src.worker_handler import handler


@pytest.fixture
def sqs_event() -> Dict[str, Any]:
    """Sample SQS event for testing with wrapped message format."""
    return {
        "Records": [
            {
                "messageId": "test-message-id",
                "receiptHandle": "test-receipt-handle",
                "body": json.dumps(
                    {
                        "message_type": "emoji_generation",
                        "payload": {
                            "job_id": "test-job-123",
                            "message_text": "Just deployed on Friday",
                            "user_description": "A test emoji",
                            "user_id": "U123456",
                            "channel_id": "C123456",
                            "timestamp": "1234567890.123456",
                            "team_id": "T123456",
                            "status": "pending",
                            "created_at": "2024-01-01T00:00:00+00:00",
                        },
                    }
                ),
                "attributes": {
                    "ApproximateReceiveCount": "1",
                    "SentTimestamp": "1234567890123",
                    "SenderId": "test-sender",
                    "ApproximateFirstReceiveTimestamp": "1234567890123",
                },
                "messageAttributes": {},
                "md5OfBody": "test-md5",
                "eventSource": "aws:sqs",
                "eventSourceARN": "arn:aws:sqs:us-east-1:123456789012:test-queue",
                "awsRegion": "us-east-1",
            }
        ]
    }


@pytest.fixture
def context():
    """Mock Lambda context."""
    context = Mock()
    context.function_name = "test-function"
    context.function_version = "1"
    context.invoked_function_arn = (
        "arn:aws:lambda:us-east-1:123456789012:function:test-function"
    )
    context.memory_limit_in_mb = 128
    context.remaining_time_in_millis = lambda: 30000
    context.aws_request_id = "test-request-id"
    context.log_group_name = "/aws/lambda/test-function"
    context.log_stream_name = "test-stream"
    return context


class TestWorkerHandler:
    """Test cases for the SQS worker Lambda handler."""

    @patch.dict(
        "os.environ",
        {
            "AWS_LAMBDA_FUNCTION_NAME": "test-function",
            "SLACK_BOT_TOKEN": "xoxb-test",
            "OPENAI_API_KEY": "sk-test",
        },
    )
    def test_lambda_handler_success(self, sqs_event, context):
        """Test successful processing of SQS message."""
        with patch("src.worker_handler.create_webhook_handler") as mock_create:
            with patch("asyncio.run") as mock_run:
                mock_create.return_value = (None, None)
                mock_run.return_value = None

                result = handler(sqs_event, context)

                assert result == {"batchItemFailures": []}
                mock_run.assert_called_once()

    @patch.dict(
        "os.environ",
        {
            "AWS_LAMBDA_FUNCTION_NAME": "test-function",
            "SLACK_BOT_TOKEN": "xoxb-test",
            "OPENAI_API_KEY": "sk-test",
        },
    )
    def test_lambda_handler_invalid_json(self, context):
        """Test handling of invalid JSON in message body."""
        invalid_event = {
            "Records": [
                {
                    "messageId": "test-message-id",
                    "body": "invalid json",
                    "receiptHandle": "test-receipt-handle",
                }
            ]
        }

        with patch("src.worker_handler.create_webhook_handler") as mock_create:
            mock_create.return_value = (None, None)

            result = handler(invalid_event, context)

            assert result == {
                "batchItemFailures": [{"itemIdentifier": "test-message-id"}]
            }

    @patch.dict(
        "os.environ",
        {
            "AWS_LAMBDA_FUNCTION_NAME": "test-function",
            "SLACK_BOT_TOKEN": "xoxb-test",
            "OPENAI_API_KEY": "sk-test",
        },
    )
    def test_lambda_handler_processing_error(self, sqs_event, context):
        """Test handling of processing errors."""
        with patch("src.worker_handler.create_webhook_handler") as mock_create:
            with patch("asyncio.run") as mock_run:
                mock_create.return_value = (None, None)
                mock_run.side_effect = Exception("Processing failed")

                result = handler(sqs_event, context)

                assert result == {
                    "batchItemFailures": [{"itemIdentifier": "test-message-id"}]
                }

    @patch.dict(
        "os.environ",
        {
            "AWS_LAMBDA_FUNCTION_NAME": "test-function",
            "SLACK_BOT_TOKEN": "xoxb-test",
            "OPENAI_API_KEY": "sk-test",
        },
    )
    def test_lambda_handler_missing_required_fields(self, context):
        """Test handling of messages with missing required fields."""
        incomplete_event = {
            "Records": [
                {
                    "messageId": "test-message-id",
                    "body": json.dumps(
                        {
                            "emoji_name": "test_emoji"
                            # Missing other required fields
                        }
                    ),
                    "receiptHandle": "test-receipt-handle",
                }
            ]
        }

        with patch("src.worker_handler.create_webhook_handler") as mock_create:
            mock_create.return_value = (None, None)

            result = handler(incomplete_event, context)

            assert result == {
                "batchItemFailures": [{"itemIdentifier": "test-message-id"}]
            }

    def test_secrets_loading_success(self):
        """Test successful loading of secrets from AWS."""
        with patch("boto3.client") as mock_boto_client:
            with patch.dict("os.environ", {"SECRETS_NAME": "test-secrets"}):
                mock_secrets_client = Mock()
                mock_boto_client.return_value = mock_secrets_client
                mock_secrets_client.get_secret_value.return_value = {
                    "SecretString": json.dumps(
                        {"SLACK_BOT_TOKEN": "xoxb-test", "OPENAI_API_KEY": "sk-test"}
                    )
                }

                from src.worker_handler import _load_secrets_from_aws

                _load_secrets_from_aws()

                assert os.environ["SLACK_BOT_TOKEN"] == "xoxb-test"
                assert os.environ["OPENAI_API_KEY"] == "sk-test"

    def test_secrets_loading_no_secrets_name(self):
        """Test graceful handling when SECRETS_NAME is not set."""
        with patch.dict("os.environ", {}, clear=True):
            from src.worker_handler import _load_secrets_from_aws

            # Should not raise an exception
            _load_secrets_from_aws()
