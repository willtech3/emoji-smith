"""Tests for EmojiGenerationJob domain entity."""

from shared.domain.entities import EmojiGenerationJob
from shared.domain.value_objects import (
    JobStatus,
    EmojiSharingPreferences,
    StylePreferences,
)


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
            sharing_preferences=EmojiSharingPreferences.default_for_context(),
            style_preferences=StylePreferences(
                style="cartoon",
                color_scheme="bright",
                detail_level="simple",
                tone="fun",
            ),
            emoji_name="smile",
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
            sharing_preferences=EmojiSharingPreferences.default_for_context(),
            style_preferences=StylePreferences(
                style="cartoon",
                color_scheme="bright",
                detail_level="simple",
                tone="fun",
            ),
            emoji_name="y",
        )
        job.mark_as_processing()
        assert job.status == JobStatus.PROCESSING
        job.mark_as_completed()
        assert job.status == JobStatus.COMPLETED
        job.mark_as_failed()
        assert job.status == JobStatus.FAILED
