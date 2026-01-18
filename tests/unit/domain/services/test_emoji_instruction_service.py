"""Tests for EmojiInstructionService."""

import pytest

from emojismith.domain.services.emoji_instruction_service import (
    EmojiInstructionService,
)
from shared.domain.value_objects import (
    EmojiSharingPreferences,
    ImageSize,
    InstructionVisibility,
    ShareLocation,
)


@pytest.mark.unit()
class TestEmojiInstructionService:
    """Test EmojiInstructionService logic."""

    @pytest.fixture()
    def service(self):
        """Create service instance."""
        return EmojiInstructionService()

    def test_build_emoji_upload_steps(self, service):
        """Test building upload steps."""
        steps = service.build_emoji_upload_steps("test_emoji")
        assert "Right-click" in steps
        assert "test_emoji" in steps

    def test_build_initial_comment_with_instructions(self, service):
        """Test building initial comment with instructions."""
        prefs = EmojiSharingPreferences(
            share_location=ShareLocation.ORIGINAL_CHANNEL,
            instruction_visibility=InstructionVisibility.EVERYONE,
            image_size=ImageSize.EMOJI_SIZE,
            include_upload_instructions=True,
        )
        comment = service.build_initial_comment("test_emoji", prefs)
        assert "Generated custom emoji: :test_emoji:" in comment
        assert "Right-click" in comment
        assert "To add this emoji to your workspace" in comment

    def test_build_initial_comment_without_instructions(self, service):
        """Test building initial comment without instructions."""
        prefs = EmojiSharingPreferences(
            share_location=ShareLocation.ORIGINAL_CHANNEL,
            instruction_visibility=InstructionVisibility.EVERYONE,
            image_size=ImageSize.EMOJI_SIZE,
            include_upload_instructions=False,
        )
        comment = service.build_initial_comment("test_emoji", prefs)
        assert "Generated custom emoji: :test_emoji:" in comment
        assert "Right-click" not in comment

    def test_build_upload_instructions(self, service):
        """Test building upload instructions for ephemeral message."""
        instructions = service.build_upload_instructions("test_emoji")
        assert "Your custom emoji `:test_emoji:` is ready!" in instructions
        assert "Right-click" in instructions
