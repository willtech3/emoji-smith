"""Unit tests for SQS worker handler.

Note: moto adds ~100ms overhead per test. Consider using class-level fixtures
for test suites to improve performance when testing with many AWS service mocks.
"""

import json
import os
from typing import Any
from unittest.mock import Mock, patch

import boto3
import pytest
from moto import mock_aws

from emojismith.infrastructure.aws.worker_handler import handler

SERVICE_PATH = (
    "emojismith.infrastructure.aws.worker_handler.create_worker_emoji_service"
)


@pytest.fixture()
def sqs_event() -> dict[str, Any]:
    """Sample SQS event for testing with direct job format."""
    return {
        "Records": [
            {
                "messageId": "test-message-id",
                "receiptHandle": "test-receipt-handle",
                "body": json.dumps(
                    {
                        "job_id": "test-job-123",
                        "message_text": "Just deployed on Friday",
                        "user_description": "A test emoji",
                        "emoji_name": "test_emoji",
                        "user_id": "U123456",
                        "channel_id": "C123456",
                        "timestamp": "1234567890.123456",
                        "team_id": "T123456",
                        "status": "PENDING",
                        "created_at": "2024-01-01T00:00:00+00:00",
                        "sharing_preferences": {
                            "share_location": "channel",
                            "instruction_visibility": "EVERYONE",
                            "image_size": "EMOJI_SIZE",
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


@pytest.fixture()
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


@pytest.mark.unit()
class TestWorkerHandler:
    """Test cases for the SQS worker Lambda handler."""

    def teardown_method(self):
        """Reset AWSSecretsLoader singleton after each test."""
        from emojismith.infrastructure.aws.secrets_loader import AWSSecretsLoader

        AWSSecretsLoader._instance = None
        AWSSecretsLoader._loaded = False

    @patch.dict(
        "os.environ",
        {
            "AWS_LAMBDA_FUNCTION_NAME": "test-function",
            "SECRETS_NAME": "test-secret",
            "AWS_DEFAULT_REGION": "us-east-1",
        },
    )
    def test_lambda_handler_processes_emoji_generation_job_successfully(
        self, sqs_event, context
    ):
        """Test successful processing of emoji generation job from SQS message."""
        with mock_aws():
            client = boto3.client("secretsmanager", region_name="us-east-1")
            client.create_secret(
                Name="test-secret",
                SecretString=json.dumps(
                    {
                        "SLACK_BOT_TOKEN": "xoxb-test",
                        "OPENAI_API_KEY": "sk-test",
                    }
                ),
            )

            with patch(SERVICE_PATH) as mock_create, patch("asyncio.run") as mock_run:
                mock_create.return_value = Mock(process_emoji_generation_job=Mock())
                mock_run.return_value = None

                result = handler(sqs_event, context)

                assert result == {"batchItemFailures": []}
                mock_run.assert_called_once()

    @patch.dict(
        "os.environ",
        {
            "AWS_LAMBDA_FUNCTION_NAME": "test-function",
            "SECRETS_NAME": "test-secret",
            "AWS_DEFAULT_REGION": "us-east-1",
        },
    )
    def test_lambda_handler_returns_failure_for_invalid_json_message(self, context):
        """Test handler returns message to DLQ when JSON parsing fails."""
        invalid_event = {
            "Records": [
                {
                    "messageId": "test-message-id",
                    "body": "invalid json",
                    "receiptHandle": "test-receipt-handle",
                }
            ]
        }

        with mock_aws():
            boto3.client("secretsmanager", region_name="us-east-1").create_secret(
                Name="test-secret",
                SecretString=json.dumps(
                    {
                        "SLACK_BOT_TOKEN": "xoxb-test",
                        "OPENAI_API_KEY": "sk-test",
                    }
                ),
            )

            with patch(SERVICE_PATH) as mock_create:
                mock_create.return_value = (None, None)

                result = handler(invalid_event, context)

                assert result == {
                    "batchItemFailures": [{"itemIdentifier": "test-message-id"}]
                }

    @patch.dict(
        "os.environ",
        {
            "AWS_LAMBDA_FUNCTION_NAME": "test-function",
            "SECRETS_NAME": "test-secret",
            "AWS_DEFAULT_REGION": "us-east-1",
        },
    )
    def test_lambda_handler_processing_error(self, sqs_event, context):
        """Test handling of processing errors."""
        with mock_aws():
            boto3.client("secretsmanager", region_name="us-east-1").create_secret(
                Name="test-secret",
                SecretString=json.dumps(
                    {
                        "SLACK_BOT_TOKEN": "xoxb-test",
                        "OPENAI_API_KEY": "sk-test",
                    }
                ),
            )

            with patch(SERVICE_PATH) as mock_create, patch("asyncio.run") as mock_run:
                mock_create.return_value = Mock(
                    process_emoji_generation_job=Mock(
                        side_effect=Exception("Processing failed")
                    )
                )
                mock_run.side_effect = Exception("Processing failed")

                result = handler(sqs_event, context)

                assert result == {
                    "batchItemFailures": [{"itemIdentifier": "test-message-id"}]
                }

    @patch.dict(
        "os.environ",
        {
            "AWS_LAMBDA_FUNCTION_NAME": "test-function",
            "SECRETS_NAME": "test-secret",
            "AWS_DEFAULT_REGION": "us-east-1",
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

        with mock_aws():
            boto3.client("secretsmanager", region_name="us-east-1").create_secret(
                Name="test-secret",
                SecretString=json.dumps(
                    {
                        "SLACK_BOT_TOKEN": "xoxb-test",
                        "OPENAI_API_KEY": "sk-test",
                    }
                ),
            )

            with patch(SERVICE_PATH) as mock_create:
                mock_create.return_value = (None, None)

                result = handler(incomplete_event, context)

                assert result == {
                    "batchItemFailures": [{"itemIdentifier": "test-message-id"}]
                }

    def test_secrets_loading_populates_environment_variables_correctly(self):
        """Test that secrets are loaded into environment variables."""
        from emojismith.infrastructure.aws.secrets_loader import AWSSecretsLoader

        AWSSecretsLoader._instance = None
        AWSSecretsLoader._loaded = False

        with mock_aws():
            client = boto3.client("secretsmanager", region_name="us-east-1")
            client.create_secret(
                Name="test-secrets",
                SecretString=json.dumps(
                    {"SLACK_BOT_TOKEN": "xoxb-test", "OPENAI_API_KEY": "sk-test"}
                ),
            )

            with patch.dict(
                os.environ,
                {"SECRETS_NAME": "test-secrets", "AWS_DEFAULT_REGION": "us-east-1"},
            ):
                AWSSecretsLoader().load_secrets()

                assert os.environ["SLACK_BOT_TOKEN"] == "xoxb-test"
                assert os.environ["OPENAI_API_KEY"] == "sk-test"

    def test_secrets_loading_no_secrets_name(self):
        """Test graceful handling when SECRETS_NAME is not set."""
        from emojismith.infrastructure.aws.secrets_loader import AWSSecretsLoader

        # Reset singleton state
        AWSSecretsLoader._instance = None
        AWSSecretsLoader._loaded = False

        with patch.dict("os.environ", {}, clear=True):
            # Should not raise an exception
            AWSSecretsLoader().load_secrets()
