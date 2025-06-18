from typing import Optional, Protocol, Tuple, runtime_checkable

from shared.domain.entities import EmojiGenerationJob


@runtime_checkable
class JobQueueProducer(Protocol):
    """Interface for enqueueing jobs."""

    async def enqueue_job(self, job: EmojiGenerationJob) -> str: ...


@runtime_checkable
class JobQueueConsumer(Protocol):
    """Interface for consuming jobs from the queue."""

    async def dequeue_job(self) -> Optional[Tuple[EmojiGenerationJob, str]]: ...

    async def complete_job(
        self, job: EmojiGenerationJob, receipt_handle: str
    ) -> None: ...

    async def get_job_status(self, job_id: str) -> Optional[str]: ...

    async def update_job_status(self, job_id: str, status: str) -> None: ...

    async def retry_failed_jobs(self, max_retries: int = 3) -> int: ...


@runtime_checkable
class JobQueueRepository(JobQueueProducer, JobQueueConsumer, Protocol):
    """Full job queue interface."""

    pass
