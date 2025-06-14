"""Tests for JobQueueRepository protocol interface."""

from emojismith.domain.repositories.job_queue_repository import JobQueueRepository


def test_job_queue_repository_protocol_defines_methods():
    """JobQueueRepository protocol specifies required methods."""
    assert hasattr(JobQueueRepository, "enqueue_job")
    assert hasattr(JobQueueRepository, "dequeue_job")
    assert hasattr(JobQueueRepository, "complete_job")
    assert hasattr(JobQueueRepository, "get_job_status")
    assert hasattr(JobQueueRepository, "update_job_status")
    assert hasattr(JobQueueRepository, "retry_failed_jobs")
