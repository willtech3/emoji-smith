"""Re-export JobQueueRepository protocol from shared package."""

from shared.domain.repositories.job_queue_repository import JobQueueRepository

__all__ = ["JobQueueRepository"]
