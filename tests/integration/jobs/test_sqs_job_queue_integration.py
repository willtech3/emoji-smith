import asyncio
import json
from typing import Tuple

import boto3
import pytest
from moto import mock_aws

from emojismith.infrastructure.jobs.sqs_job_queue import SQSJobQueue
from shared.domain.entities import EmojiGenerationJob
from shared.domain.value_objects import EmojiSharingPreferences


class AsyncClient:
    """Minimal async wrapper around a boto3 client."""

    def __init__(self, client: boto3.client) -> None:
        self._client = client

    async def __aenter__(self) -> "AsyncClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        pass

    async def send_message(self, **kwargs):
        return self._client.send_message(**kwargs)

    async def receive_message(self, **kwargs):
        return self._client.receive_message(**kwargs)

    async def delete_message(self, **kwargs):
        return self._client.delete_message(**kwargs)


class AsyncSession:
    """Async wrapper that mimics aioboto3 session behavior."""

    def __init__(self, region_name: str) -> None:
        self._session = boto3.Session(region_name=region_name)

    def client(self, service_name: str):
        return AsyncClient(self._session.client(service_name))


@pytest.fixture
def sqs_env() -> Tuple[AsyncSession, str]:
    """Create an in-memory SQS queue and session."""
    with mock_aws():
        sqs = boto3.client("sqs", region_name="us-east-1")
        queue_url = sqs.create_queue(QueueName="emoji-jobs")["QueueUrl"]
        session = AsyncSession(region_name="us-east-1")
        yield session, queue_url


@pytest.fixture
def sample_job() -> EmojiGenerationJob:
    """Return a sample emoji generation job."""
    return EmojiGenerationJob.create_new(
        message_text="integration test",
        user_description="rocket",
        emoji_name="rocket_emoji",
        user_id="U1",
        channel_id="C1",
        timestamp="1234567890.123",
        team_id="T1",
        sharing_preferences=EmojiSharingPreferences.default_for_context(),
    )


@pytest.mark.asyncio
async def test_enqueue_and_dequeue_job(
    sqs_env: Tuple[AsyncSession, str], sample_job: EmojiGenerationJob
) -> None:
    """Jobs should round trip through SQS without loss."""
    session, queue_url = sqs_env
    queue = SQSJobQueue(session=session, queue_url=queue_url)

    job_id = await queue.enqueue_job(sample_job)
    assert job_id == sample_job.job_id

    result = await queue.dequeue_job()
    assert result is not None
    dequeued, handle = result
    assert dequeued.job_id == sample_job.job_id

    await queue.complete_job(dequeued, handle)

    async with session.client("sqs") as client:
        messages = await client.receive_message(QueueUrl=queue_url, WaitTimeSeconds=0)
        assert "Messages" not in messages


@pytest.mark.asyncio
async def test_handles_message_attributes_and_delay(
    sqs_env: Tuple[AsyncSession, str], sample_job: EmojiGenerationJob
) -> None:
    """Queue should eventually return delayed messages with attributes intact."""
    session, queue_url = sqs_env
    queue = SQSJobQueue(session=session, queue_url=queue_url)

    async with session.client("sqs") as client:
        await client.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps(sample_job.to_dict()),
            DelaySeconds=1,
            MessageAttributes={"source": {"DataType": "String", "StringValue": "test"}},
        )

    await asyncio.sleep(1)
    result = await queue.dequeue_job()
    assert result is not None
    job, handle = result
    assert job.job_id == sample_job.job_id
    await queue.complete_job(job, handle)
