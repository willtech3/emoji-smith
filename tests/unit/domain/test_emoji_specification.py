"""Tests for EmojiSpecification value object."""

import pytest
from emojismith.domain.value_objects import EmojiSpecification
from shared.domain.value_objects import EmojiStylePreferences, StyleType


class TestEmojiSpecification:
    def test_emoji_specification_builds_prompt(self) -> None:
        style = EmojiStylePreferences(style_type=StyleType.PIXEL_ART)
        spec = EmojiSpecification(
            context="Deploy failed", description="facepalm", style=style
        )
        assert spec.to_prompt().startswith("Deploy failed facepalm")
        assert "pixel_art" in spec.to_prompt()

    def test_emoji_specification_with_empty_style_defaults(self) -> None:
        """Test prompt construction with empty style."""
        style = EmojiStylePreferences(style_type=StyleType.CARTOON)
        spec = EmojiSpecification(
            context="Deploy failed", description="facepalm", style=style
        )
        prompt = spec.to_prompt()
        assert "cartoon" in prompt

    def test_emoji_specification_requires_fields(self) -> None:
        with pytest.raises(ValueError):
            EmojiSpecification(context="", description="desc")
        with pytest.raises(ValueError):
            EmojiSpecification(context="ctx", description="")
