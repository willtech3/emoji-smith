import json
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import boto3
from moto import mock_aws

from emojismith.infrastructure.aws.worker_handler import handler
from shared.domain.entities import EmojiGenerationJob
from shared.domain.value_objects import EmojiSharingPreferences


@mock_aws
def test_worker_handler_processes_job_successfully():
    sqs = boto3.resource("sqs", region_name="us-east-1")
    queue = sqs.create_queue(QueueName="test-queue")

    secrets = boto3.client("secretsmanager", region_name="us-east-1")
    secrets.create_secret(
        Name="test-secret",
        SecretString=json.dumps({"SLACK_BOT_TOKEN": "xoxb", "OPENAI_API_KEY": "sk"}),
    )

    os.environ.update(
        {
            "SECRETS_NAME": "test-secret",
            "AWS_LAMBDA_FUNCTION_NAME": "fn",
            "AWS_DEFAULT_REGION": "us-east-1",
            "AWS_ACCESS_KEY_ID": "test",
            "AWS_SECRET_ACCESS_KEY": "test",
        }
    )

    job = EmojiGenerationJob.create_new(
        message_text="test",
        user_description="desc",
        emoji_name="name",
        user_id="U1",
        channel_id="C1",
        timestamp="1",
        team_id="T1",
        sharing_preferences=EmojiSharingPreferences.default_for_context(),
    )
    queue.send_message(MessageBody=json.dumps(job.to_dict()))

    msgs = queue.receive_messages(MaxNumberOfMessages=1)
    record = msgs[0]
    event = {
        "Records": [
            {
                "messageId": record.message_id,
                "receiptHandle": record.receipt_handle,
                "body": record.body,
                "eventSource": "aws:sqs",
            }
        ]
    }
    context = SimpleNamespace()

    with patch(
        "emojismith.infrastructure.aws.worker_handler.create_worker_emoji_service"
    ) as mock_create:
        mock_service = Mock(process_emoji_generation_job=AsyncMock(return_value=None))
        mock_create.return_value = mock_service
        result = handler(event, context)

    assert result == {"batchItemFailures": []}
    mock_service.process_emoji_generation_job.assert_called_once()
