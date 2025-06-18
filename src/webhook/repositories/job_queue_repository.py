"""Compatibility wrapper for job queue producer."""

from shared.domain.repositories.job_queue_repository import JobQueueProducer

JobQueueRepository = JobQueueProducer

__all__ = ["JobQueueRepository"]
