"""Tests for EmojiSharingPreferences value object."""

import pytest
from emojismith.domain.value_objects.emoji_sharing_preferences import (
    EmojiSharingPreferences,
    ShareLocation,
    InstructionVisibility,
    ImageSize,
)


class TestEmojiSharingPreferences:
    """Test emoji sharing preferences value object."""

    def test_creates_valid_preferences_for_channel_sharing(self):
        """Test creating preferences for sharing in original channel."""
        # Act
        prefs = EmojiSharingPreferences(
            share_location=ShareLocation.ORIGINAL_CHANNEL,
            instruction_visibility=InstructionVisibility.EVERYONE,
            include_upload_instructions=True,
        )

        # Assert
        assert prefs.share_location == ShareLocation.ORIGINAL_CHANNEL
        assert prefs.instruction_visibility == InstructionVisibility.EVERYONE
        assert prefs.include_upload_instructions is True

    def test_creates_valid_preferences_for_thread_sharing(self):
        """Test creating preferences for sharing in thread."""
        # Act
        prefs = EmojiSharingPreferences(
            share_location=ShareLocation.THREAD,
            instruction_visibility=InstructionVisibility.REQUESTER_ONLY,
            thread_ts="1234567890.123456",
        )

        # Assert
        assert prefs.share_location == ShareLocation.THREAD
        assert prefs.thread_ts == "1234567890.123456"

    def test_validates_thread_sharing_requires_timestamp(self):
        """Test thread sharing requires thread timestamp."""
        # Act & Assert
        with pytest.raises(ValueError, match="Thread timestamp required"):
            EmojiSharingPreferences(
                share_location=ShareLocation.THREAD,
                instruction_visibility=InstructionVisibility.EVERYONE,
                # Missing thread_ts
            )

    def test_defaults_to_include_instructions(self):
        """Test instructions are included by default."""
        # Act
        prefs = EmojiSharingPreferences(
            share_location=ShareLocation.ORIGINAL_CHANNEL,
            instruction_visibility=InstructionVisibility.EVERYONE,
        )

        # Assert
        assert prefs.include_upload_instructions is True

    def test_allows_disabling_instructions(self):
        """Test instructions can be disabled."""
        # Act
        prefs = EmojiSharingPreferences(
            share_location=ShareLocation.DM,
            instruction_visibility=InstructionVisibility.REQUESTER_ONLY,
            include_upload_instructions=False,
        )

        # Assert
        assert prefs.include_upload_instructions is False

    def test_is_immutable(self):
        """Test preferences cannot be modified after creation."""
        # Arrange
        prefs = EmojiSharingPreferences(
            share_location=ShareLocation.ORIGINAL_CHANNEL,
            instruction_visibility=InstructionVisibility.EVERYONE,
        )

        # Act & Assert
        with pytest.raises(AttributeError):
            prefs.share_location = ShareLocation.DM

    def test_equality_based_on_values(self):
        """Test preferences are equal if values are equal."""
        # Arrange
        prefs1 = EmojiSharingPreferences(
            share_location=ShareLocation.ORIGINAL_CHANNEL,
            instruction_visibility=InstructionVisibility.EVERYONE,
        )
        prefs2 = EmojiSharingPreferences(
            share_location=ShareLocation.ORIGINAL_CHANNEL,
            instruction_visibility=InstructionVisibility.EVERYONE,
        )
        prefs3 = EmojiSharingPreferences(
            share_location=ShareLocation.DM,
            instruction_visibility=InstructionVisibility.EVERYONE,
        )

        # Assert
        assert prefs1 == prefs2
        assert prefs1 != prefs3

    def test_default_for_thread_context(self):
        """Test default preferences when in thread context."""
        # Act
        prefs = EmojiSharingPreferences.default_for_context(
            is_in_thread=True, thread_ts="1234567890.123456"
        )

        # Assert
        assert prefs.share_location == ShareLocation.THREAD
        assert prefs.thread_ts == "1234567890.123456"
        assert prefs.instruction_visibility == InstructionVisibility.EVERYONE
        assert prefs.image_size == ImageSize.EMOJI_SIZE

    def test_default_for_channel_context(self):
        """Test default preferences when in channel context."""
        # Act
        prefs = EmojiSharingPreferences.default_for_context(is_in_thread=False)

        # Assert
        assert prefs.share_location == ShareLocation.NEW_THREAD
        assert prefs.thread_ts is None
        assert prefs.instruction_visibility == InstructionVisibility.EVERYONE
        assert prefs.image_size == ImageSize.EMOJI_SIZE

    def test_can_specify_full_size_image(self):
        """Test preferences can specify full size image."""
        # Act
        prefs = EmojiSharingPreferences(
            share_location=ShareLocation.NEW_THREAD,
            instruction_visibility=InstructionVisibility.EVERYONE,
            image_size=ImageSize.FULL_SIZE,
        )

        # Assert
        assert prefs.image_size == ImageSize.FULL_SIZE
