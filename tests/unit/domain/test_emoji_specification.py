"""Tests for EmojiSpecification value object."""

import pytest
from emojismith.domain.value_objects import EmojiSpecification


class TestEmojiSpecification:
    """Validate EmojiSpecification rules."""

    def test_valid_specification_creation(self) -> None:
        spec = EmojiSpecification(context="hello", description="smile")
        assert spec.size_px == 128
        assert spec.image_format == "PNG"
        assert spec.max_bytes == 64_000

    def test_invalid_size_raises(self) -> None:
        with pytest.raises(ValueError):
            EmojiSpecification(context="a", description="b", size_px=256)

    def test_invalid_format_raises(self) -> None:
        with pytest.raises(ValueError):
            EmojiSpecification(context="a", description="b", image_format="JPEG")

    def test_invalid_max_bytes_raises(self) -> None:
        with pytest.raises(ValueError):
            EmojiSpecification(context="a", description="b", max_bytes=100_000)
