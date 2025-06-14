"""Job queue repository protocol for domain layer."""

from typing import Dict, Any, Optional, Protocol
from emojismith.domain.entities.emoji_generation_job import EmojiGenerationJob


class JobQueueRepository(Protocol):
    """Protocol for job queue operations."""

    async def enqueue_job(self, job_data: Dict[str, Any]) -> str:
        """Enqueue a new emoji generation job."""
        ...

    async def dequeue_job(self) -> Optional[EmojiGenerationJob]:
        """Dequeue the next pending job for processing."""
        ...

    async def complete_job(self, job: EmojiGenerationJob) -> None:
        """Mark job as completed and remove from queue."""
        ...

    async def get_job_status(self, job_id: str) -> Optional[str]:
        """Get the current status of a job."""
        ...

    async def update_job_status(self, job_id: str, status: str) -> None:
        """Update the status of a job."""
        ...

    async def retry_failed_jobs(self, max_retries: int = 3) -> int:
        """Retry failed jobs that haven't exceeded max retries."""
        ...
