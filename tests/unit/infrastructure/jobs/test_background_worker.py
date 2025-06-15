"""Tests for BackgroundWorker job processing loop."""

"""Tests for the BackgroundWorker behaviour."""

import asyncio
import pytest

from emojismith.infrastructure.jobs.background_worker import BackgroundWorker


class DummyJobQueue:
    """Minimal job queue that always returns no work."""

    async def dequeue_job(self):
        await asyncio.sleep(0)
        return None

    async def update_job_status(self, job_id, status):
        pass

    async def complete_job(self, job, receipt_handle):
        pass


class DummyService:
    """Dummy emoji service used by the worker."""

    async def process_emoji_generation_job(self, job):
        pass


@pytest.mark.asyncio
async def test_worker_can_be_stopped() -> None:
    """Worker exits its loop once stop() is called."""
    job_queue = DummyJobQueue()
    service = DummyService()
    worker = BackgroundWorker(job_queue, service, poll_interval=0)

    task = asyncio.create_task(worker.start())
    await asyncio.sleep(0)
    await worker.stop()
    await asyncio.wait_for(task, timeout=0.1)
