"""Tests for EmojiSpecification value object."""

import pytest
from emojismith.domain.value_objects import EmojiSpecification
from shared.domain.value_objects import EmojiStylePreferences, StyleType


class TestEmojiSpecification:
    def test_prompt_construction(self) -> None:
        prefs = EmojiStylePreferences(style_type=StyleType.PIXEL_ART)
        spec = EmojiSpecification(
            context="Deploy failed", description="facepalm", style_preferences=prefs
        )
        prompt = spec.to_prompt()
        assert prompt.startswith("Deploy failed facepalm")
        assert "pixel art" in prompt

    def test_prompt_construction_without_style(self) -> None:
        """Test prompt construction with empty style."""
        prefs = EmojiStylePreferences(style_type=StyleType.CARTOON)
        spec = EmojiSpecification(
            context="Deploy failed", description="facepalm", style_preferences=prefs
        )
        prompt = spec.to_prompt()
        assert "cartoon" in prompt

    def test_requires_fields(self) -> None:
        with pytest.raises(ValueError):
            EmojiSpecification(context="", description="desc")
        with pytest.raises(ValueError):
            EmojiSpecification(context="ctx", description="")
