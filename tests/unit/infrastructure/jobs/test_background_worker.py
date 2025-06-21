"""Tests for BackgroundWorker job processing loop using real services."""

import asyncio
import os
import time
from unittest.mock import AsyncMock, patch
from types import SimpleNamespace

import pytest

from emojismith.app import create_worker_emoji_service
from emojismith.infrastructure.jobs.background_worker import BackgroundWorker
from shared.domain.entities import EmojiGenerationJob
from shared.domain.value_objects import EmojiSharingPreferences, EmojiStylePreferences


class InMemoryJobQueue:
    """In-memory queue implementation for testing."""

    def __init__(self):
        self._queue = asyncio.Queue()
        self._job_status = {}
        self._job_completed = {}  # Track completion events per job

    async def enqueue_job(self, job: EmojiGenerationJob) -> str:
        """Add job to the queue."""
        await self._queue.put((job, f"receipt-{job.job_id}"))
        self._job_status[job.job_id] = "pending"
        self._job_completed[job.job_id] = asyncio.Event()
        return job.job_id

    async def dequeue_job(self):
        """Get next job from the queue."""
        try:
            # Non-blocking get with timeout
            return await asyncio.wait_for(self._queue.get(), timeout=0.1)
        except asyncio.TimeoutError:
            return None

    async def update_job_status(self, job_id: str, status: str):
        """Update job status."""
        self._job_status[job_id] = status
        if status == "completed" and job_id in self._job_completed:
            self._job_completed[job_id].set()

    async def complete_job(self, job, receipt_handle: str):
        """Mark job as completed."""
        await self.update_job_status(job.job_id, "completed")

    def get_pending_jobs(self) -> int:
        """Get count of pending jobs."""
        return self._queue.qsize()

    def get_job_status(self, job_id: str) -> str:
        """Get status of a specific job (public API)."""
        return self._job_status.get(job_id, "unknown")

    async def wait_for_job(self, job_id: str, timeout: float = 5.0) -> bool:
        """Wait for a job to complete with timeout."""
        if job_id not in self._job_completed:
            return False
        try:
            await asyncio.wait_for(self._job_completed[job_id].wait(), timeout=timeout)
            return True
        except asyncio.TimeoutError:
            return False


@pytest.mark.asyncio
async def test_background_worker_end_to_end_processes_job() -> None:
    """Test worker processes jobs using real services with minimal mocking."""
    start_time = time.time()

    # Set dummy environment variables
    os.environ["SLACK_BOT_TOKEN"] = "xoxb-test-token"
    os.environ["OPENAI_API_KEY"] = "sk-test-key"

    # Minimal PNG image data for stubbed OpenAI response
    png_b64 = (
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGP4"
        "z8AAAAMBAQDJ/pLvAAAAAElFTkSuQmCC"
    )

    # Create stubbed Slack client at HTTP boundary
    mock_slack_client = AsyncMock()
    mock_slack_client.files_upload_v2 = AsyncMock(
        return_value={
            "ok": True,
            "file": {"url_private": "https://files.slack.com/test.png"},
        }
    )
    mock_slack_client.chat_postMessage = AsyncMock(
        return_value={"ok": True, "ts": "1234567890.123456"}
    )
    mock_slack_client.chat_postEphemeral = AsyncMock(return_value={"ok": True})
    mock_slack_client.conversations_join = AsyncMock(return_value={"ok": True})

    # Create stubbed OpenAI client at HTTP boundary
    mock_openai_client = AsyncMock()
    mock_openai_client.models = SimpleNamespace(retrieve=AsyncMock(return_value=None))
    mock_openai_client.chat = SimpleNamespace(
        completions=SimpleNamespace(
            create=AsyncMock(
                return_value=SimpleNamespace(
                    choices=[
                        SimpleNamespace(
                            message=SimpleNamespace(
                                content="Fire emoji based on urgency"
                            )
                        )
                    ]
                )
            )
        )
    )
    mock_openai_client.images = SimpleNamespace(
        generate=AsyncMock(
            return_value=SimpleNamespace(data=[SimpleNamespace(b64_json=png_b64)])
        )
    )

    # Create real emoji service with stubbed external clients
    with (
        patch("emojismith.app.AsyncWebClient", return_value=mock_slack_client),
        patch("emojismith.app.AsyncOpenAI", return_value=mock_openai_client),
    ):
        emoji_service = create_worker_emoji_service()

    # Create in-memory queue
    job_queue = InMemoryJobQueue()

    # Create worker with real service
    worker = BackgroundWorker(
        job_queue=job_queue,
        emoji_service=emoji_service,
        max_concurrent_jobs=1,
        poll_interval=0,  # No delay for testing
    )

    # Create test job
    job = EmojiGenerationJob.create_new(
        message_text="Deploy on Friday? Are you crazy?",
        user_description="fire emoji for urgency",
        emoji_name="fire_emoji",
        user_id="U123456",
        channel_id="C789012",
        timestamp="1234567890.123456",
        team_id="T999999",
        sharing_preferences=EmojiSharingPreferences.default_for_context(),
        style_preferences=EmojiStylePreferences(),
    )

    # Enqueue job
    await job_queue.enqueue_job(job)
    assert job_queue.get_pending_jobs() == 1

    # Start worker and let it process the job
    worker_task = asyncio.create_task(worker.start())

    # Wait for job to be processed using deterministic signal
    job_completed = await job_queue.wait_for_job(job.job_id, timeout=2.0)
    assert job_completed, "Job did not complete within timeout"

    # Stop worker
    await worker.stop()

    # Cancel the worker task
    worker_task.cancel()
    try:
        await worker_task
    except asyncio.CancelledError:
        pass

    # Verify job was processed using public API
    assert job_queue.get_pending_jobs() == 0
    assert job_queue.get_job_status(job.job_id) == "completed"

    # Verify Slack file upload was called
    mock_slack_client.files_upload_v2.assert_called_once()
    upload_call = mock_slack_client.files_upload_v2.call_args
    assert upload_call.kwargs["filename"] == "fire_emoji.png"
    assert upload_call.kwargs["channels"] == ["C789012"]

    # Verify OpenAI was called for generation
    mock_openai_client.images.generate.assert_called_once()

    # Log test execution time for performance monitoring
    elapsed = time.time() - start_time
    print(f"Test execution time: {elapsed:.2f}s")


@pytest.mark.asyncio
async def test_background_worker_with_multiple_jobs_processes_concurrently() -> None:
    """Test worker can process multiple jobs concurrently."""
    start_time = time.time()

    # Set dummy environment variables
    os.environ["SLACK_BOT_TOKEN"] = "xoxb-test-token"
    os.environ["OPENAI_API_KEY"] = "sk-test-key"

    # Minimal PNG image data
    png_b64 = (
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGP4"
        "z8AAAAMBAQDJ/pLvAAAAAElFTkSuQmCC"
    )

    # Create stubbed clients
    mock_slack_client = AsyncMock()
    mock_slack_client.files_upload_v2 = AsyncMock(
        return_value={
            "ok": True,
            "file": {"url_private": "https://files.slack.com/test.png"},
        }
    )
    mock_slack_client.chat_postMessage = AsyncMock(
        return_value={"ok": True, "ts": "1234567890.123456"}
    )
    mock_slack_client.chat_postEphemeral = AsyncMock(return_value={"ok": True})
    mock_slack_client.conversations_join = AsyncMock(return_value={"ok": True})

    mock_openai_client = AsyncMock()
    mock_openai_client.models = SimpleNamespace(retrieve=AsyncMock(return_value=None))
    mock_openai_client.chat = SimpleNamespace(
        completions=SimpleNamespace(
            create=AsyncMock(
                return_value=SimpleNamespace(
                    choices=[SimpleNamespace(message=SimpleNamespace(content="emoji"))]
                )
            )
        )
    )
    mock_openai_client.images = SimpleNamespace(
        generate=AsyncMock(
            return_value=SimpleNamespace(data=[SimpleNamespace(b64_json=png_b64)])
        )
    )

    with (
        patch("emojismith.app.AsyncWebClient", return_value=mock_slack_client),
        patch("emojismith.app.AsyncOpenAI", return_value=mock_openai_client),
    ):
        emoji_service = create_worker_emoji_service()

    job_queue = InMemoryJobQueue()
    worker = BackgroundWorker(
        job_queue=job_queue,
        emoji_service=emoji_service,
        max_concurrent_jobs=3,
        poll_interval=0,
    )

    # Create multiple jobs
    jobs = []
    for i in range(3):
        job = EmojiGenerationJob.create_new(
            message_text=f"Test message {i}",
            user_description=f"test emoji {i}",
            emoji_name=f"test_emoji_{i}",
            user_id="U123456",
            channel_id="C789012",
            timestamp=f"123456789{i}.123456",
            team_id="T999999",
            sharing_preferences=EmojiSharingPreferences.default_for_context(),
            style_preferences=EmojiStylePreferences(),
        )
        await job_queue.enqueue_job(job)
        jobs.append(job)

    # Start worker
    worker_task = asyncio.create_task(worker.start())

    # Wait for all jobs to be processed using deterministic signals
    wait_tasks = [job_queue.wait_for_job(job.job_id, timeout=2.0) for job in jobs]
    results = await asyncio.gather(*wait_tasks)
    assert all(results), "Not all jobs completed within timeout"

    # Stop worker
    await worker.stop()
    worker_task.cancel()
    try:
        await worker_task
    except asyncio.CancelledError:
        pass

    # Verify all jobs were processed using public API
    assert job_queue.get_pending_jobs() == 0
    for job in jobs:
        assert job_queue.get_job_status(job.job_id) == "completed"

    # Verify Slack was called for each job
    assert mock_slack_client.files_upload_v2.call_count == 3

    # Log test execution time for performance monitoring
    elapsed = time.time() - start_time
    print(f"Test execution time: {elapsed:.2f}s")
