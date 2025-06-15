"""Tests for BackgroundWorker job processing loop."""

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
async def test_processes_emoji_jobs_until_stopped(monkeypatch):
    """Test that BackgroundWorker starts and stops as expected."""
    job_queue = DummyJobQueue()
    service = DummyService()
    worker = BackgroundWorker(
        job_queue, service, max_concurrent_jobs=1, poll_interval=0
    )
    with pytest.raises(KeyboardInterrupt):
        await worker.start()
    # After crash, running flag remains True until stop is called
    await worker.stop()
    assert not worker.running


@pytest.mark.asyncio
async def test_handles_stop_gracefully_when_not_running():
    """Calling stop when the worker isn't running should succeed."""
    job_queue = DummyJobQueue()
    service = DummyService()
    worker = BackgroundWorker(job_queue, service)
    await worker.stop()
    assert not worker.running
