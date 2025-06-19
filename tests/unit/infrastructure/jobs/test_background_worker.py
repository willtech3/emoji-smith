import asyncio
import base64
import os
from io import BytesIO
from typing import Optional, Tuple
from unittest.mock import AsyncMock, patch

import pytest
from PIL import Image

from emojismith.app import create_worker_emoji_service
from emojismith.infrastructure.jobs.background_worker import BackgroundWorker
from shared.domain.entities import EmojiGenerationJob
from shared.domain.value_objects import EmojiSharingPreferences
from emojismith.domain.repositories.job_queue_repository import JobQueueRepository


class InMemoryJobQueue(JobQueueRepository):
    """Simple in-memory job queue for testing."""

    def __init__(self) -> None:
        self._queue: asyncio.Queue[Tuple[EmojiGenerationJob, str]] = asyncio.Queue()

    async def enqueue_job(self, job: EmojiGenerationJob) -> str:
        await self._queue.put((job, "handle"))
        return job.job_id

    async def dequeue_job(self) -> Optional[Tuple[EmojiGenerationJob, str]]:
        try:
            return self._queue.get_nowait()
        except asyncio.QueueEmpty:
            return None

    async def complete_job(self, job: EmojiGenerationJob, receipt_handle: str) -> None:
        pass

    async def get_job_status(self, job_id: str) -> Optional[str]:
        return None

    async def update_job_status(self, job_id: str, status: str) -> None:
        pass

    async def retry_failed_jobs(self, max_retries: int = 3) -> int:
        return 0


@pytest.mark.asyncio
async def test_worker_processes_job_end_to_end() -> None:
    """BackgroundWorker processes a queued job using real services."""
    queue = InMemoryJobQueue()

    # Prepare fake OpenAI responses
    img_buf = BytesIO()
    Image.new("RGBA", (128, 128), "white").save(img_buf, format="PNG")
    b64_image = base64.b64encode(img_buf.getvalue()).decode()

    openai_client = AsyncMock()
    openai_client.chat.completions.create.return_value = AsyncMock(
        choices=[AsyncMock(message=AsyncMock(content="ok"))]
    )
    openai_client.images.generate.return_value = AsyncMock(
        data=[AsyncMock(b64_json=b64_image)]
    )

    slack_client = AsyncMock()
    slack_client.admin_emoji_add.return_value = {"ok": True}
    slack_client.reactions_add.return_value = {"ok": True}
    slack_client.files_upload_v2.return_value = {
        "ok": True,
        "file": {"url_private": "https://example.com"},
    }
    slack_client.conversations_join.return_value = {"ok": True}
    slack_client.chat_postMessage.return_value = {"ok": True, "ts": "1"}
    slack_client.chat_postEphemeral.return_value = {"ok": True}

    with (
        patch.dict(
            os.environ,
            {"SLACK_BOT_TOKEN": "xoxb-test", "OPENAI_API_KEY": "sk-test"},
            clear=True,
        ),
        patch("emojismith.app.AsyncWebClient", return_value=slack_client),
        patch("emojismith.app.AsyncOpenAI", return_value=openai_client),
    ):
        service = create_worker_emoji_service()

    worker = BackgroundWorker(queue, service, poll_interval=0)

    job = EmojiGenerationJob.create_new(
        message_text="msg",
        user_description="desc",
        emoji_name="demo",
        user_id="U1",
        channel_id="C1",
        timestamp="123",
        team_id="T1",
        sharing_preferences=EmojiSharingPreferences.default_for_context(),
    )

    await queue.enqueue_job(job)

    start = asyncio.get_event_loop().time()
    task = asyncio.create_task(worker.start())
    await asyncio.sleep(0.1)
    await worker.stop()
    await task
    duration = asyncio.get_event_loop().time() - start

    assert duration < 1.0
    slack_client.reactions_add.assert_called_once()
    slack_client.files_upload_v2.assert_called_once()
