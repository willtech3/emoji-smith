import asyncio

import boto3
import pytest
from moto import mock_aws

from emojismith.infrastructure.jobs.sqs_job_queue import SQSJobQueue
from shared.domain.entities import EmojiGenerationJob
from shared.domain.value_objects import EmojiSharingPreferences


class AsyncClientWrapper:
    """Async wrapper around boto3 client methods."""

    def __init__(self, client: boto3.client) -> None:
        self._client = client

    async def __aenter__(self) -> "AsyncClientWrapper":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    async def create_queue(self, **kwargs):
        return await asyncio.to_thread(self._client.create_queue, **kwargs)

    async def send_message(self, **kwargs):
        return await asyncio.to_thread(self._client.send_message, **kwargs)

    async def receive_message(self, **kwargs):
        return await asyncio.to_thread(self._client.receive_message, **kwargs)

    async def delete_message(self, **kwargs):
        return await asyncio.to_thread(self._client.delete_message, **kwargs)


class AsyncBoto3Session:
    """Return async client wrappers compatible with SQSJobQueue."""

    def client(self, service_name: str, **kwargs) -> AsyncClientWrapper:
        client = boto3.client(service_name, region_name="us-east-1", **kwargs)
        return AsyncClientWrapper(client)


@pytest.mark.integration()
@pytest.mark.asyncio()
async def test_enqueue_and_complete_job_flow() -> None:
    """Enqueue and dequeue a job using a real SQS backend."""
    with mock_aws():
        session = AsyncBoto3Session()
        async with session.client("sqs") as client:
            queue_url = (await client.create_queue(QueueName="test-queue"))["QueueUrl"]

        job_queue = SQSJobQueue(session=session, queue_url=queue_url)

        job_entity = EmojiGenerationJob.create_new(
            message_text="Integration test",
            user_description="party parrot",
            emoji_name="party_parrot",
            user_id="U1",
            channel_id="C1",
            timestamp="111",
            team_id="T1",
            sharing_preferences=EmojiSharingPreferences.default_for_context(),
        )
        from shared.domain.dtos import EmojiGenerationJobDto

        job = EmojiGenerationJobDto(**job_entity.to_dict())

        job_id = await job_queue.enqueue_job(job)
        assert job_id == job.job_id

        result = await job_queue.dequeue_job()
        assert result is not None
        dequeued_job, receipt_handle = result
        assert dequeued_job.job_id == job.job_id

        await job_queue.complete_job(dequeued_job, receipt_handle)

        async with session.client("sqs") as client:
            messages = await client.receive_message(QueueUrl=queue_url)
            assert "Messages" not in messages


@pytest.mark.integration()
@pytest.mark.asyncio()
async def test_dequeue_empty_queue_returns_none() -> None:
    """Dequeuing an empty queue should return None."""
    with mock_aws():
        session = AsyncBoto3Session()
        async with session.client("sqs") as client:
            queue_url = (await client.create_queue(QueueName="test-queue-empty"))[
                "QueueUrl"
            ]

        job_queue = SQSJobQueue(session=session, queue_url=queue_url)

        result = await job_queue.dequeue_job()
        assert result is None
