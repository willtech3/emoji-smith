"""Background worker for processing emoji generation jobs."""

import asyncio
import logging
from typing import Any

from emojismith.application.services.emoji_service import EmojiCreationService
from emojismith.domain.repositories.job_queue_repository import JobQueueRepository


class BackgroundWorker:
    """Background worker that processes emoji generation jobs from the queue."""

    def __init__(
        self,
        job_queue: JobQueueRepository,
        emoji_service: EmojiCreationService,
        max_concurrent_jobs: int = 5,
        poll_interval: int = 5,
    ) -> None:
        self._job_queue = job_queue
        self._emoji_service = emoji_service
        self._max_concurrent_jobs = max_concurrent_jobs
        self._poll_interval = poll_interval
        self._logger = logging.getLogger(__name__)
        self._running = False
        self._semaphore = asyncio.Semaphore(max_concurrent_jobs)
        self._tasks: set[asyncio.Task] = set()

    @property
    def running(self) -> bool:
        """Return True if the worker is currently running."""
        return self._running

    async def start(self) -> None:
        """Start the background worker."""
        self._running = True
        self._logger.info("Starting background worker")

        try:
            await self._process_jobs()
        except Exception as e:
            self._logger.exception("Background worker crashed", extra={"error": str(e)})
            raise

    async def stop(self) -> None:
        """Stop the background worker."""
        self._running = False
        self._logger.info("Stopping background worker")

        # Wait for all pending tasks to complete
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)

    async def _process_jobs(self) -> None:
        """Main processing loop."""
        while self._running:
            try:
                # Get next job from queue
                job_tuple = await self._job_queue.dequeue_job()

                if job_tuple:
                    job, receipt_handle = job_tuple
                    # Process job concurrently within semaphore limits
                    task = asyncio.create_task(
                        self._process_single_job(job, receipt_handle)
                    )
                    self._tasks.add(task)
                    task.add_done_callback(self._tasks.discard)
                else:
                    # No jobs available, wait before polling again
                    await asyncio.sleep(self._poll_interval)

            except Exception as e:
                self._logger.error(
                    "Error in job processing loop", extra={"error": str(e)}
                )
                await asyncio.sleep(self._poll_interval)

    async def _process_single_job(self, job: Any, receipt_handle: str) -> None:
        """Process a single emoji generation job."""
        async with self._semaphore:
            self._logger.info(
                "Processing emoji generation job",
                extra={"job_id": job.job_id, "user_id": job.user_id},
            )

            try:
                # Update job status to processing
                await self._job_queue.update_job_status(job.job_id, "processing")

                # Process the emoji generation
                await self._emoji_service.process_emoji_generation_job(job)

                # Mark job as completed
                await self._job_queue.complete_job(job, receipt_handle)
                await self._job_queue.update_job_status(job.job_id, "completed")

                self._logger.info(
                    "Successfully completed emoji generation job",
                    extra={"job_id": job.job_id},
                )

            except Exception as e:
                self._logger.error(
                    "Failed to process emoji generation job",
                    extra={"job_id": job.job_id, "error": str(e)},
                )

                # Update job status to failed
                await self._job_queue.update_job_status(job.job_id, "failed")

                # Re-queue for retry if appropriate
                # (SQS handles this through Dead Letter Queues)
