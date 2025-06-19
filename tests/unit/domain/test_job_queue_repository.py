"""Tests for JobQueueRepository protocol interface."""

from emojismith.domain.repositories.job_queue_repository import (
    JobQueueProducer,
    JobQueueConsumer,
    JobQueueRepository,
)


def test_job_queue_repository_protocol_defines_methods() -> None:
    """Job queue repository protocols specify required methods."""
    assert hasattr(JobQueueProducer, "enqueue_job")
    assert hasattr(JobQueueConsumer, "dequeue_job")
    assert hasattr(JobQueueConsumer, "complete_job")
    assert hasattr(JobQueueConsumer, "get_job_status")
    assert hasattr(JobQueueConsumer, "update_job_status")
    assert hasattr(JobQueueConsumer, "retry_failed_jobs")
    assert hasattr(JobQueueRepository, "enqueue_job")
    assert hasattr(JobQueueRepository, "dequeue_job")
