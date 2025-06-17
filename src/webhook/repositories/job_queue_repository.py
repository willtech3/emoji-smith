"""Job queue repository interface for webhook package."""

from abc import ABC, abstractmethod
from shared.domain.entities import EmojiGenerationJob


class JobQueueRepository(ABC):
    """Repository interface for job queue operations."""

    @abstractmethod
    async def enqueue_job(self, job: EmojiGenerationJob) -> str:
        """Enqueue an emoji generation job."""
        pass
