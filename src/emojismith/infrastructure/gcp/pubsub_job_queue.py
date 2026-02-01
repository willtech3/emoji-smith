"""Pub/Sub implementation of the JobQueueProducer protocol."""

import asyncio
import dataclasses
import json
import os

from google.cloud import pubsub_v1  # type: ignore[attr-defined]

from shared.domain.dtos import EmojiGenerationJobDto
from shared.domain.repositories.job_queue_repository import JobQueueProducer


class PubSubJobQueue(JobQueueProducer):
    """Publishes jobs to Google Cloud Pub/Sub."""

    def __init__(
        self, project_id: str | None = None, topic_id: str | None = None
    ) -> None:
        self.project_id = project_id or os.environ["PUBSUB_PROJECT"]
        self.topic_id = topic_id or os.environ["PUBSUB_TOPIC"]
        self._publisher = pubsub_v1.PublisherClient()
        self._topic_path = self._publisher.topic_path(self.project_id, self.topic_id)

    async def enqueue_job(self, job: EmojiGenerationJobDto) -> str:
        """Publish a job to Pub/Sub and return the message ID."""
        job_dict = dataclasses.asdict(job)
        data = json.dumps(job_dict).encode("utf-8")

        def publish_sync() -> str:
            future = self._publisher.publish(self._topic_path, data)
            return str(future.result())

        loop = asyncio.get_running_loop()
        message_id = await loop.run_in_executor(None, publish_sync)
        return message_id
