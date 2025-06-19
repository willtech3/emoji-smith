import asyncio
import base64
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from emojismith.app import create_worker_emoji_service
from emojismith.infrastructure.jobs.background_worker import BackgroundWorker
from shared.domain.entities import EmojiGenerationJob
from shared.domain.value_objects import EmojiSharingPreferences


class InMemoryJobQueue:
    """Simple in-memory job queue for integration tests."""

    def __init__(self) -> None:
        self._queue: asyncio.Queue[tuple[EmojiGenerationJob, str]] = asyncio.Queue()
        self.status: dict[str, str] = {}

    async def enqueue_job(self, job: EmojiGenerationJob) -> str:
        await self._queue.put((job, "rh"))
        self.status[job.job_id] = "PENDING"
        return job.job_id

    async def dequeue_job(self) -> tuple[EmojiGenerationJob, str] | None:
        if self._queue.empty():
            return None
        return await self._queue.get()

    async def complete_job(self, job: EmojiGenerationJob, receipt_handle: str) -> None:
        self.status[job.job_id] = "COMPLETED"

    async def get_job_status(self, job_id: str) -> str | None:
        return self.status.get(job_id)

    async def update_job_status(self, job_id: str, status: str) -> None:
        self.status[job_id] = status

    async def retry_failed_jobs(self, max_retries: int = 3) -> int:
        return 0


@pytest.mark.asyncio
async def test_worker_processes_job_end_to_end(monkeypatch) -> None:
    os.environ["SLACK_BOT_TOKEN"] = "xoxb-test"
    os.environ["OPENAI_API_KEY"] = "sk-test"

    # Minimal PNG image encoded as base64
    png_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGP4z8AAAAMBAQDJ/pLvAAAAAElFTkSuQmCC"

    class FakeSlackClient:
        def __init__(self, *_: object, **__: object) -> None:
            self.admin_emoji_add = AsyncMock(return_value={"ok": True})
            self.reactions_add = AsyncMock()
            self.files_upload_v2 = AsyncMock(
                return_value={"ok": True, "file": {"url_private": "http://u"}}
            )
            self.chat_postMessage = AsyncMock(return_value={"ts": "t"})
            self.chat_postEphemeral = AsyncMock()
            self.conversations_join = AsyncMock()

    class FakeOpenAI:
        def __init__(self, *_: object, **__: object) -> None:
            self.models = SimpleNamespace(retrieve=AsyncMock(return_value=None))
            self.chat = SimpleNamespace(
                completions=SimpleNamespace(
                    create=AsyncMock(
                        return_value=SimpleNamespace(
                            choices=[
                                SimpleNamespace(message=SimpleNamespace(content="ok"))
                            ]
                        )
                    )
                )
            )
            self.images = SimpleNamespace(
                generate=AsyncMock(
                    return_value=SimpleNamespace(
                        data=[SimpleNamespace(b64_json=png_b64)]
                    )
                )
            )

    with (
        patch("emojismith.app.AsyncWebClient", FakeSlackClient),
        patch("emojismith.app.AsyncOpenAI", FakeOpenAI),
    ):
        service = create_worker_emoji_service()

    job_queue = InMemoryJobQueue()
    worker = BackgroundWorker(
        job_queue, service, max_concurrent_jobs=1, poll_interval=0
    )

    job = EmojiGenerationJob.create_new(
        message_text="Test",
        user_description="desc",
        emoji_name="test",
        user_id="U1",
        channel_id="C1",
        timestamp="1.0",
        team_id="T1",
        sharing_preferences=EmojiSharingPreferences.default_for_context(),
    )

    await job_queue.enqueue_job(job)

    task = asyncio.create_task(worker.start())
    await asyncio.sleep(0.05)
    await worker.stop()
    await asyncio.wait_for(task, timeout=1)

    slack_client = service._file_sharing_repo._client  # type: ignore[attr-defined]
    assert slack_client.files_upload_v2.called
