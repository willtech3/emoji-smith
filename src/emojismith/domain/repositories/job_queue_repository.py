"""Re-export job queue repository interfaces from shared domain."""

from shared.domain.repositories import (
    JobQueueConsumer,
    JobQueueProducer,
    JobQueueRepository,
)

__all__ = ["JobQueueConsumer", "JobQueueProducer", "JobQueueRepository"]
