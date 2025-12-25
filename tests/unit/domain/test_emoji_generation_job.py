"""Tests for EmojiGenerationJob domain entity."""

import uuid

import pytest

from shared.domain.entities import EmojiGenerationJob
from shared.domain.value_objects import EmojiSharingPreferences, JobStatus


@pytest.mark.unit()
class TestEmojiGenerationJob:
    """Test creation and state transitions for EmojiGenerationJob."""

    def test_create_new_when_trace_id_not_provided_generates_trace_id(self):
        """create_new should generate a trace_id for cross-Lambda correlation."""
        job = EmojiGenerationJob.create_new(
            message_text="hello",
            user_description="smile",
            user_id="U1",
            channel_id="C1",
            timestamp="ts",
            team_id="T1",
            sharing_preferences=EmojiSharingPreferences.default_for_context(),
            emoji_name="smile",
        )

        assert job.trace_id
        # Should be a UUID string
        uuid.UUID(job.trace_id)

    def test_create_new_when_trace_id_provided_uses_value(self):
        """create_new should use provided trace_id verbatim."""
        job = EmojiGenerationJob.create_new(
            message_text="hello",
            user_description="smile",
            user_id="U1",
            channel_id="C1",
            timestamp="ts",
            team_id="T1",
            sharing_preferences=EmojiSharingPreferences.default_for_context(),
            emoji_name="smile",
            trace_id="trace-xyz",
        )

        assert job.trace_id == "trace-xyz"

    def test_emoji_generation_job_round_trip_persists_status(self):
        job = EmojiGenerationJob.create_new(
            message_text="hello",
            user_description="smile",
            user_id="U1",
            channel_id="C1",
            timestamp="ts",
            team_id="T1",
            sharing_preferences=EmojiSharingPreferences.default_for_context(),
            emoji_name="smile",
        )
        assert job.job_id
        assert job.status == JobStatus.PENDING
        data = job.to_dict()
        assert data["job_id"] == job.job_id
        assert data["trace_id"] == job.trace_id
        restored = EmojiGenerationJob.from_dict(data)
        assert restored.job_id == job.job_id
        assert restored.trace_id == job.trace_id
        assert restored.status == JobStatus.PENDING

    def test_from_dict_when_trace_id_missing_defaults_to_empty_string(self):
        """Backward compat: missing trace_id should default to empty string."""
        original_job = EmojiGenerationJob.create_new(
            message_text="hello",
            user_description="smile",
            user_id="U1",
            channel_id="C1",
            timestamp="ts",
            team_id="T1",
            sharing_preferences=EmojiSharingPreferences.default_for_context(),
            emoji_name="smile",
        )
        data = original_job.to_dict()
        del data["trace_id"]

        restored = EmojiGenerationJob.from_dict(data)
        assert restored.trace_id == ""

    def test_emoji_generation_job_lifecycle_transitions_correctly(self):
        job = EmojiGenerationJob.create_new(
            message_text="x",
            user_description="y",
            user_id="U1",
            channel_id="C1",
            timestamp="ts",
            team_id="T1",
            sharing_preferences=EmojiSharingPreferences.default_for_context(),
            emoji_name="y",
        )
        job.mark_as_processing()
        assert job.status == JobStatus.PROCESSING
        job.mark_as_completed()
        assert job.status == JobStatus.COMPLETED
        job.mark_as_failed()
        assert job.status == JobStatus.FAILED

    def test_to_dict_when_default_provider_includes_google_gemini(self):
        """Test that default image_provider is included in to_dict."""
        job = EmojiGenerationJob.create_new(
            message_text="hello",
            user_description="smile",
            user_id="U1",
            channel_id="C1",
            timestamp="ts",
            team_id="T1",
            sharing_preferences=EmojiSharingPreferences.default_for_context(),
            emoji_name="smile",
        )
        data = job.to_dict()
        assert data["image_provider"] == "google_gemini"

    def test_from_dict_when_provider_missing_defaults_to_google_gemini(self):
        """Test backward compat: missing image_provider defaults to google_gemini."""
        # Create a valid job and get its dict representation
        original_job = EmojiGenerationJob.create_new(
            message_text="hello",
            user_description="smile",
            user_id="U1",
            channel_id="C1",
            timestamp="ts",
            team_id="T1",
            sharing_preferences=EmojiSharingPreferences.default_for_context(),
            emoji_name="smile",
        )
        data = original_job.to_dict()
        # Remove image_provider to simulate old job data
        del data["image_provider"]

        job = EmojiGenerationJob.from_dict(data)
        assert job.image_provider == "google_gemini"

    def test_from_dict_when_provider_present_preserves_value(self):
        """Test that image_provider value is preserved through serialization."""
        # Create a valid job with google_gemini provider
        original_job = EmojiGenerationJob.create_new(
            message_text="hello",
            user_description="smile",
            user_id="U1",
            channel_id="C1",
            timestamp="ts",
            team_id="T1",
            sharing_preferences=EmojiSharingPreferences.default_for_context(),
            emoji_name="smile",
            image_provider="google_gemini",
        )
        data = original_job.to_dict()

        job = EmojiGenerationJob.from_dict(data)
        assert job.image_provider == "google_gemini"

    def test_create_new_with_image_provider_stores_value(self):
        """Test that create_new stores the image_provider value."""
        job = EmojiGenerationJob.create_new(
            message_text="hello",
            user_description="smile",
            user_id="U1",
            channel_id="C1",
            timestamp="ts",
            team_id="T1",
            sharing_preferences=EmojiSharingPreferences.default_for_context(),
            emoji_name="smile",
            image_provider="google_gemini",
        )
        assert job.image_provider == "google_gemini"

    def test_image_provider_round_trip_preserves_value(self):
        """Test that image_provider is preserved through to_dict/from_dict cycle."""
        job = EmojiGenerationJob.create_new(
            message_text="hello",
            user_description="smile",
            user_id="U1",
            channel_id="C1",
            timestamp="ts",
            team_id="T1",
            sharing_preferences=EmojiSharingPreferences.default_for_context(),
            emoji_name="smile",
            image_provider="google_gemini",
        )
        data = job.to_dict()
        restored = EmojiGenerationJob.from_dict(data)
        assert restored.image_provider == "google_gemini"
