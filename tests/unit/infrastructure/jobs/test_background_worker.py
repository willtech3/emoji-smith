"""Tests for BackgroundWorker job processing loop."""

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


@pytest.mark.asyncio
async def test_processes_job_end_to_end(monkeypatch):
    """Process a queued job using real services with stubbed HTTP clients."""
    import base64
    from io import BytesIO
    import os
    from types import SimpleNamespace
    from PIL import Image

    from emojismith.app import create_worker_emoji_service
    from shared.domain.entities import EmojiGenerationJob
    from shared.domain.value_objects import EmojiSharingPreferences

    class InMemoryQueue:
        """Minimal in-memory job queue for the worker."""

        def __init__(self, job):
            self._job = job
            self.calls = 0

        async def enqueue_job(self, job):
            self._job = job

        async def dequeue_job(self):
            self.calls += 1
            if self.calls == 1:
                return self._job, "rh"
            raise KeyboardInterrupt

        async def complete_job(self, job, receipt_handle):
            self.completed = True

        async def update_job_status(self, job_id, status):
            self.status = status

        async def get_job_status(self, job_id):
            return None

        async def retry_failed_jobs(self, max_retries: int = 3):
            return 0

    class DummySlackClient:
        """Stub Slack client capturing HTTP calls."""

        def __init__(self):
            self.admin_emoji_add = AsyncMock(return_value={"ok": True})
            self.reactions_add = AsyncMock()
            self.conversations_join = AsyncMock()
            self.files_upload_v2 = AsyncMock(
                return_value={"ok": True, "file": {"url_private": "http://x"}}
            )
            self.chat_postMessage = AsyncMock(return_value={"ts": "1"})
            self.chat_postEphemeral = AsyncMock()

    img = Image.new("RGBA", (4, 4), "red")
    buf = BytesIO()
    img.save(buf, format="PNG")
    b64_image = base64.b64encode(buf.getvalue()).decode()

    class DummyOpenAI:
        def __init__(self):
            self.models = SimpleNamespace(retrieve=AsyncMock())
            self.chat = SimpleNamespace(
                completions=SimpleNamespace(
                    create=AsyncMock(
                        return_value=SimpleNamespace(
                            choices=[
                                SimpleNamespace(message=SimpleNamespace(content="p"))
                            ]
                        )
                    )
                )
            )
            self.images = SimpleNamespace(
                generate=AsyncMock(
                    return_value=SimpleNamespace(
                        data=[SimpleNamespace(b64_json=b64_image)]
                    )
                )
            )

    slack_client = DummySlackClient()
    openai_client = DummyOpenAI()
    monkeypatch.setattr("emojismith.app.AsyncWebClient", lambda token: slack_client)
    monkeypatch.setattr("emojismith.app.AsyncOpenAI", lambda api_key: openai_client)

    with monkeypatch.context() as m:
        m.setitem(os.environ, "SLACK_BOT_TOKEN", "xoxb-test")
        m.setitem(os.environ, "OPENAI_API_KEY", "sk-test")
        service = create_worker_emoji_service()

    job = EmojiGenerationJob.create_new(
        message_text="hi",
        user_description="wave",
        emoji_name="wave",
        user_id="U1",
        channel_id="C1",
        timestamp="1",
        team_id="T1",
        sharing_preferences=EmojiSharingPreferences.default_for_context(),
    )

    queue = InMemoryQueue(job)
    worker = BackgroundWorker(queue, service, max_concurrent_jobs=1, poll_interval=0)

    with pytest.raises(KeyboardInterrupt):
        await worker.start()
    await worker.stop()

    assert slack_client.files_upload_v2.called
