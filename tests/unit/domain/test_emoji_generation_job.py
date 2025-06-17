"""Tests for EmojiGenerationJob domain entity."""

from shared.domain.entities import EmojiGenerationJob
from shared.domain.value_objects import JobStatus


class TestEmojiGenerationJob:
    """Test creation and state transitions for EmojiGenerationJob."""

    def test_create_new_and_to_from_dict(self):
        job = EmojiGenerationJob.create_new(
            message_text="hello",
            user_description="smile",
            user_id="U1",
            channel_id="C1",
            timestamp="ts",
            team_id="T1",
        )
        assert job.job_id
        assert job.status == JobStatus.PENDING
        data = job.to_dict()
        assert data["job_id"] == job.job_id
        restored = EmojiGenerationJob.from_dict(data)
        assert restored.job_id == job.job_id
        assert restored.status == JobStatus.PENDING

    def test_status_transitions(self):
        job = EmojiGenerationJob.create_new(
            message_text="x",
            user_description="y",
            user_id="U1",
            channel_id="C1",
            timestamp="ts",
            team_id="T1",
        )
        job.mark_processing()
        assert job.is_processing()
        job.mark_completed()
        assert job.is_completed()
        job.mark_failed()
        assert job.is_failed()
