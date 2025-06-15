"""Tests for BackgroundWorker job processing loop."""

import asyncio
import pytest

from emojismith.infrastructure.jobs.background_worker import BackgroundWorker


class DummyJobQueue:
    """Dummy job queue for testing."""

    def __init__(self):
        self.calls = 0

    async def dequeue_job(self):
        self.calls += 1
        # After one iteration, stop the loop by raising
        if self.calls > 1:
            raise KeyboardInterrupt
        return None

    async def update_job_status(self, job_id, status):
        pass

    async def complete_job(self, job, receipt_handle):
        pass


class DummyService:
    """Dummy emoji service for testing."""

    async def process_emoji_generation_job(self, job):
        pass


@pytest.mark.asyncio
async def test_worker_runs_until_stopped():
    """Worker start returns once stop() is called."""
    job_queue = DummyJobQueue()
    service = DummyService()
    worker = BackgroundWorker(
        job_queue, service, max_concurrent_jobs=1, poll_interval=0
    )

    task = asyncio.create_task(worker.start())
    await asyncio.sleep(0)  # allow loop to start
    await worker.stop()
    await asyncio.wait_for(task, timeout=1)
    assert job_queue.calls > 0


@pytest.mark.asyncio
async def test_worker_stop_is_idempotent():
    """Calling stop multiple times should not error."""
    job_queue = DummyJobQueue()
    service = DummyService()
    worker = BackgroundWorker(job_queue, service, poll_interval=0)
    task = asyncio.create_task(worker.start())
    await asyncio.sleep(0)
    await worker.stop()
    await worker.stop()  # second call should be a no-op
    await asyncio.wait_for(task, timeout=1)
