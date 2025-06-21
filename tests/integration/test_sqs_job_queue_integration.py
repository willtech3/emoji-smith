import json
import boto3
import pytest
from moto import mock_aws

from emojismith.infrastructure.jobs.sqs_job_queue import SQSJobQueue
from shared.domain.entities import EmojiGenerationJob
from shared.domain.value_objects import EmojiSharingPreferences


class AsyncClient:
    """Async wrapper around boto3 client."""

    def __init__(self, client: boto3.client) -> None:
        self._client = client

    async def __aenter__(self) -> "AsyncClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    async def send_message(self, **kwargs):
        return self._client.send_message(**kwargs)

    async def receive_message(self, **kwargs):
        return self._client.receive_message(**kwargs)

    async def delete_message(self, **kwargs):
        return self._client.delete_message(**kwargs)


class AsyncSession:
    """Provide async context manager interface for boto3 Session."""

    def __init__(self, session: boto3.Session) -> None:
        self._session = session

    def client(self, *args, **kwargs) -> AsyncClient:
        return AsyncClient(self._session.client(*args, **kwargs))


@pytest.mark.asyncio
async def test_enqueue_dequeue_and_complete_cycle() -> None:
    with mock_aws():
        boto_client = boto3.client("sqs", region_name="us-east-1")
        queue_url = boto_client.create_queue(QueueName="emoji-jobs")["QueueUrl"]
        session = AsyncSession(boto3.Session(region_name="us-east-1"))

        job_queue = SQSJobQueue(session=session, queue_url=queue_url)
        job = EmojiGenerationJob.create_new(
            message_text="test msg",
            user_description="desc",
            emoji_name="emoji",
            user_id="U1",
            channel_id="C1",
            timestamp="123",
            team_id="T1",
            sharing_preferences=EmojiSharingPreferences.default_for_context(),
        )

        await job_queue.enqueue_job(job)
        result = await job_queue.dequeue_job()
        assert result is not None
        dequeued, handle = result
        assert dequeued.job_id == job.job_id

        await job_queue.complete_job(dequeued, handle)

        async with session.client("sqs", region_name="us-east-1") as client:
            remaining = await client.receive_message(
                QueueUrl=queue_url, WaitTimeSeconds=1
            )
            assert "Messages" not in remaining


@pytest.mark.asyncio
async def test_dequeue_empty_queue_returns_none() -> None:
    with mock_aws():
        boto_client = boto3.client("sqs", region_name="us-east-1")
        queue_url = boto_client.create_queue(QueueName="emoji-jobs")["QueueUrl"]
        session = AsyncSession(boto3.Session(region_name="us-east-1"))

        job_queue = SQSJobQueue(session=session, queue_url=queue_url)
        result = await job_queue.dequeue_job()
        assert result is None
