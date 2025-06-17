"""Job queue repository protocol for domain layer."""

from typing import Optional, Protocol, Tuple
from emojismith.domain.entities.emoji_generation_job import EmojiGenerationJob


class JobQueueRepository(Protocol):
    """Protocol for job queue operations."""

    async def enqueue_job(self, job: EmojiGenerationJob) -> str:
        """Enqueue a new emoji generation job."""
        ...

    async def dequeue_job(self) -> Optional[Tuple[EmojiGenerationJob, str]]:
        """Dequeue the next pending job for processing.

        Returns a tuple of the job and an opaque receipt handle used for
        acknowledging completion.
        """
        ...

    async def complete_job(self, job: EmojiGenerationJob, receipt_handle: str) -> None:
        """Mark job as completed and remove from queue using the receipt handle."""
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

