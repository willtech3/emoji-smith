"""Tests for BackgroundWorker job processing loop."""

import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock

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

    async def complete_job(self, job):
        pass


class DummyService:
    """Dummy emoji service for testing."""

    async def process_emoji_generation_job(self, job):
        pass


@pytest.mark.asyncio
async def test_worker_start_and_stop(monkeypatch):
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
    assert not worker._running


@pytest.mark.asyncio
async def test_worker_stop_sets_running_false():
    """Test that stop() sets the running flag to False."""
    job_queue = DummyJobQueue()
    service = DummyService()
    worker = BackgroundWorker(job_queue, service)
    worker._running = True
    await worker.stop()
    assert not worker._running


@pytest.mark.asyncio
async def test_process_single_job_success():
    job_queue = AsyncMock()
    service = AsyncMock()
    worker = BackgroundWorker(job_queue, service)
    job = SimpleNamespace(job_id="1", user_id="u")
    await worker._process_single_job(job)
    job_queue.update_job_status.assert_any_call("1", "processing")
    job_queue.complete_job.assert_awaited_once_with(job)
    job_queue.update_job_status.assert_called_with("1", "completed")
    service.process_emoji_generation_job.assert_awaited_once_with(job)
