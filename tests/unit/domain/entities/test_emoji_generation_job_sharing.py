"""Tests for EmojiGenerationJob with sharing preferences."""

from shared.domain.entities import EmojiGenerationJob
from shared.domain.value_objects import (
    EmojiSharingPreferences,
    ShareLocation,
    InstructionVisibility,
    ImageSize,
)


class TestEmojiGenerationJobSharing:
    """Test emoji generation job with sharing preferences."""

    def test_creates_job_with_sharing_preferences(self):
        """Test creating job with sharing preferences."""
        # Arrange
        prefs = EmojiSharingPreferences(
            share_location=ShareLocation.ORIGINAL_CHANNEL,
            instruction_visibility=InstructionVisibility.EVERYONE,
            image_size=ImageSize.EMOJI_SIZE,
        )

        # Act
        job = EmojiGenerationJob.create_new(
            message_text="Deploy failed",
            user_description="facepalm",
            user_id="U123",
            channel_id="C456",
            timestamp="123.456",
            team_id="T789",
            sharing_preferences=prefs,
        )

        # Assert
        assert job.sharing_preferences == prefs
        assert job.sharing_preferences.share_location == ShareLocation.ORIGINAL_CHANNEL

    def test_job_dict_includes_sharing_preferences(self):
        """Test job serialization includes sharing preferences."""
        # Arrange
        prefs = EmojiSharingPreferences(
            share_location=ShareLocation.THREAD,
            instruction_visibility=InstructionVisibility.SUBMITTER_ONLY,
            image_size=ImageSize.EMOJI_SIZE,
            thread_ts="123.456",
        )
        job = EmojiGenerationJob.create_new(
            message_text="Bug report",
            user_description="bug emoji",
            user_id="U123",
            channel_id="C456",
            timestamp="123.456",
            team_id="T789",
            sharing_preferences=prefs,
        )

        # Act
        job_dict = job.to_dict()

        # Assert
        assert "sharing_preferences" in job_dict
        assert job_dict["sharing_preferences"]["share_location"] == "thread"
        assert (
            job_dict["sharing_preferences"]["instruction_visibility"]
            == "SUBMITTER_ONLY"
        )
        assert job_dict["sharing_preferences"]["thread_ts"] == "123.456"

    def test_job_from_dict_restores_sharing_preferences(self):
        """Test job deserialization restores sharing preferences."""
        # Arrange
        job_dict = {
            "job_id": "test-123",
            "message_text": "Deploy failed",
            "user_description": "facepalm",
            "user_id": "U123",
            "channel_id": "C456",
            "timestamp": "123.456",
            "team_id": "T789",
            "status": "PENDING",
            "created_at": "2024-01-01T00:00:00+00:00",
            "sharing_preferences": {
                "share_location": "dm",
                "instruction_visibility": "EVERYONE",
                "image_size": "EMOJI_SIZE",
                "include_upload_instructions": True,
                "thread_ts": None,
            },
        }

        # Act
        job = EmojiGenerationJob.from_dict(job_dict)

        # Assert
        assert job.sharing_preferences.share_location == ShareLocation.DIRECT_MESSAGE
        assert (
            job.sharing_preferences.instruction_visibility
            == InstructionVisibility.EVERYONE
        )
        assert job.sharing_preferences.include_upload_instructions is True

    def test_job_defaults_to_new_thread_if_no_preferences(self):
        """Test job defaults to new thread when not in thread context."""
        # Arrange
        default_prefs = EmojiSharingPreferences.default_for_context(is_in_thread=False)

        # Act
        job = EmojiGenerationJob.create_new(
            message_text="Deploy failed",
            user_description="facepalm",
            user_id="U123",
            channel_id="C456",
            timestamp="123.456",
            team_id="T789",
            sharing_preferences=default_prefs,
        )

        # Assert
        assert job.sharing_preferences is not None
        assert job.sharing_preferences.share_location == ShareLocation.ORIGINAL_CHANNEL
        assert (
            job.sharing_preferences.instruction_visibility
            == InstructionVisibility.EVERYONE
        )

    def test_job_defaults_to_existing_thread_when_in_thread(self):
        """Test job defaults to existing thread when in thread context."""
        # Arrange
        default_prefs = EmojiSharingPreferences.default_for_context(
            is_in_thread=True, thread_ts="123.456"
        )

        # Act
        job = EmojiGenerationJob.create_new(
            message_text="Bug in thread",
            user_description="bug emoji",
            user_id="U123",
            channel_id="C456",
            timestamp="123.456",
            team_id="T789",
            sharing_preferences=default_prefs,
            thread_ts="123.456",
        )

        # Assert
        assert job.sharing_preferences is not None
        assert job.sharing_preferences.share_location == ShareLocation.THREAD
        assert job.sharing_preferences.thread_ts == "123.456"
        assert (
            job.sharing_preferences.instruction_visibility
            == InstructionVisibility.EVERYONE
        )
