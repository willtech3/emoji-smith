"""SQS job queue implementation for webhook package."""

import json
import logging
import boto3

from shared.domain.repositories.job_queue_repository import JobQueueProducer
from shared.domain.entities import EmojiGenerationJob


class SQSJobQueue(JobQueueProducer):
    """SQS implementation of job queue for webhook package."""

    def __init__(self, queue_url: str) -> None:
        self._queue_url = queue_url
        self._sqs_client = boto3.client("sqs")
        self._logger = logging.getLogger(__name__)

    async def enqueue_job(self, job: EmojiGenerationJob) -> str:
        """Enqueue an emoji generation job to SQS."""
        message_body = json.dumps(job.to_dict())

        response = self._sqs_client.send_message(
            QueueUrl=self._queue_url,
            MessageBody=message_body,
        )

        self._logger.info(
            "Enqueued emoji generation job",
            extra={
                "job_id": job.job_id,
                "message_id": response["MessageId"],
                "user_id": job.user_id,
            },
        )

        return job.job_id
