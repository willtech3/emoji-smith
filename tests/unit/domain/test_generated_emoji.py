"""Tests for GeneratedEmoji entity.

Note: Image format and dimension validation is now handled by
EmojiValidationService, so these tests focus on basic entity validation.
"""

import pytest
from emojismith.domain.entities.generated_emoji import GeneratedEmoji


class TestGeneratedEmoji:
    def test_generated_emoji_with_valid_data_initializes(self) -> None:
        """Test creating valid emoji entity."""
        data = b"fake_png_data"
        emoji = GeneratedEmoji(image_data=data, name="test")
        assert emoji.name == "test"
        assert emoji.image_data == data

    def test_generated_emoji_with_empty_image_raises_error(self) -> None:
        """Test that empty image data is rejected."""
        with pytest.raises(ValueError, match="image_data is required"):
            GeneratedEmoji(image_data=b"", name="test")

    def test_generated_emoji_with_empty_name_raises_error(self) -> None:
        """Test that empty name is rejected."""
        with pytest.raises(ValueError, match="name is required"):
            GeneratedEmoji(image_data=b"fake_data", name="")

    def test_generated_emoji_with_large_file_rejected(self) -> None:
        """Test that files exceeding 64KB are rejected."""
        big_data = b"0" * (64 * 1024)  # Exactly 64KB, should fail
        with pytest.raises(ValueError, match="64KB"):
            GeneratedEmoji(image_data=big_data, name="big")

    def test_generated_emoji_under_limit_allowed(self) -> None:
        """Test that files just under 64KB are accepted."""
        data = b"0" * (64 * 1024 - 1)  # Just under 64KB
        emoji = GeneratedEmoji(image_data=data, name="test")
        assert len(emoji.image_data) == 64 * 1024 - 1

    def test_generated_emoji_is_immutable(self) -> None:
        """Test that entity is immutable (frozen dataclass)."""
        emoji = GeneratedEmoji(image_data=b"data", name="test")
        with pytest.raises(AttributeError):
            emoji.name = "changed"  # type: ignore[misc]
