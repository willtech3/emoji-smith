"""Tests for BackgroundWorker job processing loop."""

import asyncio
import pytest
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


class DummyJob:
    job_id = "jid"
    user_id = "uid"


class SingleJobQueue(DummyJobQueue):
    """Queue that returns one job then raises to stop the loop."""

    async def dequeue_job(self):
        self.calls += 1
        if self.calls == 1:
            return DummyJob()
        raise KeyboardInterrupt


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
    """_process_single_job processes job and marks completed."""
    job_queue = DummyJobQueue()
    service = DummyService()
    job_queue.update_job_status = AsyncMock()
    job_queue.complete_job = AsyncMock()
    service.process_emoji_generation_job = AsyncMock()
    worker = BackgroundWorker(job_queue, service)
    job = DummyJob()

    await worker._process_single_job(job)

    service.process_emoji_generation_job.assert_called_once_with(job)
    job_queue.update_job_status.assert_any_call(job.job_id, "processing")
    job_queue.update_job_status.assert_any_call(job.job_id, "completed")
    job_queue.complete_job.assert_called_once_with(job)


@pytest.mark.asyncio
async def test_process_single_job_failure():
    """Failure during processing updates job status to failed."""
    job_queue = DummyJobQueue()
    service = DummyService()
    job_queue.update_job_status = AsyncMock()
    job_queue.complete_job = AsyncMock()
    service.process_emoji_generation_job = AsyncMock(side_effect=Exception("boom"))
    worker = BackgroundWorker(job_queue, service)
    job = DummyJob()

    await worker._process_single_job(job)

    job_queue.update_job_status.assert_any_call(job.job_id, "processing")
    job_queue.update_job_status.assert_any_call(job.job_id, "failed")
    job_queue.complete_job.assert_not_called()


@pytest.mark.asyncio
async def test_process_jobs_runs_single_job():
    """start() processes a queued job then stops on exception."""
    job_queue = SingleJobQueue()
    service = DummyService()
    service.process_emoji_generation_job = AsyncMock()
    job_queue.update_job_status = AsyncMock()
    job_queue.complete_job = AsyncMock()

    worker = BackgroundWorker(job_queue, service, poll_interval=0)

    with pytest.raises(KeyboardInterrupt):
        await worker.start()
    await asyncio.sleep(0)
    service.process_emoji_generation_job.assert_called_once()
    job_queue.update_job_status.assert_any_call("jid", "processing")
