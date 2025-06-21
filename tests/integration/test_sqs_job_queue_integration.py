import json
import os
import pytest
from moto.server import ThreadedMotoServer
import aioboto3

from emojismith.infrastructure.jobs.sqs_job_queue import SQSJobQueue
from shared.domain.entities import EmojiGenerationJob
from shared.domain.value_objects import EmojiSharingPreferences


@pytest.fixture
def moto_sqs_server() -> str:
    server = ThreadedMotoServer(port=5006)
    server.start()
    _, port = server.get_host_and_port()
    os.environ.update(
        {
            "AWS_ACCESS_KEY_ID": "test",
            "AWS_SECRET_ACCESS_KEY": "test",
            "AWS_DEFAULT_REGION": "us-east-1",
        }
    )
    yield f"http://localhost:{port}"
    server.stop()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_enqueue_and_dequeue_job_flow(moto_sqs_server: str) -> None:
    session = aioboto3.Session(
        aws_access_key_id="testing",
        aws_secret_access_key="testing",
        aws_session_token="testing",
        region_name="us-east-1",
    )
    async with session.client("sqs", endpoint_url=moto_sqs_server) as client:
        queue_url = (await client.create_queue(QueueName="test-queue"))["QueueUrl"]

    job_queue = SQSJobQueue(
        session=session, queue_url=queue_url, endpoint_url=moto_sqs_server
    )
    job = EmojiGenerationJob.create_new(
        message_text="Friday deploy",
        user_description="facepalm reaction",
        emoji_name="facepalm_reaction",
        user_id="U12345",
        channel_id="C67890",
        timestamp="1234567890.123456",
        team_id="T11111",
        sharing_preferences=EmojiSharingPreferences.default_for_context(),
    )

    await job_queue.enqueue_job(job)

    result = await job_queue.dequeue_job()
    assert result is not None
    dequeued_job, handle = result
    assert dequeued_job.job_id == job.job_id

    await job_queue.complete_job(dequeued_job, handle)

    result_after_delete = await job_queue.dequeue_job()
    assert result_after_delete is None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_message_body_and_attributes(moto_sqs_server: str) -> None:
    session = aioboto3.Session(
        aws_access_key_id="testing",
        aws_secret_access_key="testing",
        aws_session_token="testing",
        region_name="us-east-1",
    )
    async with session.client("sqs", endpoint_url=moto_sqs_server) as client:
        queue_url = (await client.create_queue(QueueName="test-queue"))["QueueUrl"]

    job_queue = SQSJobQueue(
        session=session, queue_url=queue_url, endpoint_url=moto_sqs_server
    )
    job = EmojiGenerationJob.create_new(
        message_text="hi",
        user_description="wave",
        emoji_name="wave",
        user_id="U1",
        channel_id="C1",
        timestamp="111.222",
        team_id="T1",
        sharing_preferences=EmojiSharingPreferences.default_for_context(),
    )

    await job_queue.enqueue_job(job)

    async with session.client("sqs", endpoint_url=moto_sqs_server) as client:
        resp = await client.receive_message(QueueUrl=queue_url, MaxNumberOfMessages=1)
    messages = resp.get("Messages", [])
    assert len(messages) == 1
    body = json.loads(messages[0]["Body"])
    assert body["job_id"] == job.job_id
    assert "MessageAttributes" not in messages[0]
