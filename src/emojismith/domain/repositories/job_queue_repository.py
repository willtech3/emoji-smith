"""Re-export job queue repository interfaces from shared domain."""

from shared.domain.repositories import (
    JobQueueProducer,
    JobQueueConsumer,
    JobQueueRepository,
)

__all__ = ["JobQueueProducer", "JobQueueConsumer", "JobQueueRepository"]
