"""Tests for GeneratedEmoji entity.

Note: Image format and dimension validation is now handled by
EmojiValidationService, so these tests focus on basic entity validation.
"""

import pytest

from emojismith.domain.entities.generated_emoji import GeneratedEmoji
from emojismith.domain.exceptions import ValidationError


@pytest.mark.unit()
class TestGeneratedEmoji:
    def test_generated_emoji_when_valid_returns_entity(self) -> None:
        """Test creating valid emoji entity."""
        data = b"fake_png_data"
        emoji = GeneratedEmoji(image_data=data, name="test")
        assert emoji.name == "test"
        assert emoji.image_data == data

    def test_generated_emoji_empty_image_data_raises_error(self) -> None:
        """Test that empty image data is rejected."""
        with pytest.raises(ValueError, match="image_data is required"):
            GeneratedEmoji(image_data=b"", name="test")

    def test_generated_emoji_empty_name_raises_error(self) -> None:
        """Test that empty name is rejected."""
        with pytest.raises(ValueError, match="name is required"):
            GeneratedEmoji(image_data=b"fake_data", name="")

    def test_generated_emoji_over_size_limit_raises_error(self) -> None:
        """Test that files exceeding 64KB are rejected."""
        big_data = b"0" * (64 * 1024)  # Exactly 64KB, should fail
        with pytest.raises(ValueError, match="64KB"):
            GeneratedEmoji(image_data=big_data, name="big")

    def test_generated_emoji_under_size_limit_is_accepted(self) -> None:
        """Test that files just under 64KB are accepted."""
        data = b"0" * (64 * 1024 - 1)  # Just under 64KB
        emoji = GeneratedEmoji(image_data=data, name="test")
        assert len(emoji.image_data) == 64 * 1024 - 1

    def test_generated_emoji_object_is_immutable(self) -> None:
        """Test that entity is immutable (frozen dataclass)."""
        emoji = GeneratedEmoji(image_data=b"data", name="test")
        with pytest.raises(AttributeError):
            emoji.name = "changed"  # type: ignore[misc]

    def test_needs_resizing_returns_true_for_large_images(self) -> None:
        """Emoji exceeding resize threshold should need resizing."""
        large_data = b"0" * (55 * 1024)  # 55KB - over the 50KB threshold
        emoji = GeneratedEmoji(image_data=large_data, name="large", format="png")
        assert emoji.needs_resizing() is True

    def test_needs_resizing_returns_false_for_small_images(self) -> None:
        """Small emojis should not need resizing."""
        small_data = b"0" * 1024  # 1KB
        emoji = GeneratedEmoji(image_data=small_data, name="small", format="png")
        assert emoji.needs_resizing() is False

    def test_validate_format_accepts_valid_formats(self) -> None:
        """Valid image formats should be accepted."""
        for format in ["png", "gif", "jpg"]:
            emoji = GeneratedEmoji(image_data=b"data", name="test", format=format)
            # Should not raise an exception
            emoji.validate_format()

    def test_validate_format_rejects_invalid_formats(self) -> None:
        """Invalid image formats should be rejected at construction time."""
        with pytest.raises(ValidationError, match="Unsupported format: webp"):
            GeneratedEmoji(image_data=b"data", name="test", format="webp")

    def test_default_format_is_png(self) -> None:
        """Default format should be png."""
        emoji = GeneratedEmoji(image_data=b"data", name="test")
        assert emoji.format == "png"
