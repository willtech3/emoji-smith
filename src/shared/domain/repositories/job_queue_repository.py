"""Protocol definitions for job queue repositories."""

from typing import Optional, Protocol, Tuple

from shared.domain.entities import EmojiGenerationJob


class JobQueueProducer(Protocol):
    """Interface for queue producers."""

    async def enqueue_job(self, job: EmojiGenerationJob) -> str: ...


class JobQueueConsumer(Protocol):
    """Interface for queue consumers."""

    async def dequeue_job(self) -> Optional[Tuple[EmojiGenerationJob, str]]: ...

    async def complete_job(
        self, job: EmojiGenerationJob, receipt_handle: str
    ) -> None: ...

    async def get_job_status(self, job_id: str) -> Optional[str]: ...

    async def update_job_status(self, job_id: str, status: str) -> None: ...

    async def retry_failed_jobs(self, max_retries: int = 3) -> int: ...


class JobQueueRepository(JobQueueProducer, JobQueueConsumer, Protocol):
    """Complete job queue interface."""

    pass
