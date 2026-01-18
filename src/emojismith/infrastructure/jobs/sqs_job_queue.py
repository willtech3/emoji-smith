"""SQS-based job queue implementation."""

import json
import logging
from dataclasses import asdict
from typing import Any

from emojismith.domain.repositories.job_queue_repository import JobQueueRepository
from shared.domain.dtos import EmojiGenerationJobDto


class SQSJobQueue(JobQueueRepository):
    """SQS-based implementation of job queue."""

    def __init__(self, session: Any, queue_url: str) -> None:
        self._session = session
        self._queue_url = queue_url
        self._logger = logging.getLogger(__name__)

    @property
    def queue_url(self) -> str:
        """Return the configured SQS queue URL."""
        return self._queue_url

    async def enqueue_job(self, job: EmojiGenerationJobDto) -> str:
        """Enqueue a new emoji generation job."""
        # Send job directly to SQS
        message_body = json.dumps(asdict(job))

        async with self._session.client("sqs") as sqs_client:
            response = await sqs_client.send_message(
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

    async def dequeue_job(self) -> tuple[EmojiGenerationJobDto, str] | None:
        """Dequeue the next pending job for processing.

        Returns a tuple containing the job and the SQS receipt handle used
        to acknowledge completion.
        """
        async with self._session.client("sqs") as sqs_client:
            response = await sqs_client.receive_message(
                QueueUrl=self._queue_url,
                MaxNumberOfMessages=1,
                WaitTimeSeconds=20,  # Long polling for efficiency
                MessageAttributeNames=["All"],
            )

        messages = response.get("Messages", [])
        if not messages:
            return None

        message = messages[0]

        try:
            # Parse job data from message body
            job_data = json.loads(message["Body"])
            job = EmojiGenerationJobDto(**job_data)
            receipt_handle = message["ReceiptHandle"]

            self._logger.info(
                "Dequeued emoji generation job",
                extra={"job_id": job.job_id, "user_id": job.user_id},
            )

            return job, receipt_handle

        except (json.JSONDecodeError, KeyError, TypeError) as e:
            self._logger.error(
                "Failed to parse job message",
                extra={"message_id": message.get("MessageId"), "error": str(e)},
            )
            # Delete malformed message
            await self._delete_message(message["ReceiptHandle"])
            return None

    async def complete_job(
        self, job: EmojiGenerationJobDto, receipt_handle: str
    ) -> None:
        """Mark job as completed and remove from queue."""
        await self._delete_message(receipt_handle)
        self._logger.info(
            "Completed and removed job from queue", extra={"job_id": job.job_id}
        )

    async def _delete_message(self, receipt_handle: str | None) -> None:
        """Delete message from SQS queue if a receipt handle is present."""
        if not receipt_handle:
            return
        async with self._session.client("sqs") as sqs_client:
            await sqs_client.delete_message(
                QueueUrl=self._queue_url, ReceiptHandle=receipt_handle
            )

    async def get_job_status(self, job_id: str) -> str | None:
        """Get the current status of a job."""
        # For SQS implementation, we'll rely on message visibility
        # In production, you might want to use DynamoDB for status tracking
        return None

    async def update_job_status(self, job_id: str, status: str) -> None:
        """Update the status of a job."""
        # For SQS implementation, status is managed by queue visibility
        # In production, you might want to use DynamoDB for status tracking
        self._logger.info(
            "Job status updated", extra={"job_id": job_id, "status": status}
        )

    async def retry_failed_jobs(self, max_retries: int = 3) -> int:
        """Retry failed jobs that haven't exceeded max retries."""
        # SQS handles retries through Dead Letter Queues and redrive policies
        # This would be configured in the infrastructure setup
        return 0
