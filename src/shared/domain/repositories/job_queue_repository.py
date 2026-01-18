"""Protocol definitions for job queue repositories."""

from typing import Protocol, runtime_checkable

from shared.domain.dtos import EmojiGenerationJobDto


@runtime_checkable
class JobQueueProducer(Protocol):
    """Interface for queue producers."""

    async def enqueue_job(self, job: EmojiGenerationJobDto) -> str: ...


@runtime_checkable
class JobQueueConsumer(Protocol):
    """Interface for queue consumers."""

    async def dequeue_job(self) -> tuple[EmojiGenerationJobDto, str] | None: ...

    async def complete_job(
        self, job: EmojiGenerationJobDto, receipt_handle: str
    ) -> None: ...

    async def get_job_status(self, job_id: str) -> str | None: ...

    async def update_job_status(self, job_id: str, status: str) -> None: ...

    async def retry_failed_jobs(self, max_retries: int = 3) -> int: ...


@runtime_checkable
class JobQueueRepository(JobQueueProducer, JobQueueConsumer, Protocol):
    """Complete job queue interface."""

    pass
