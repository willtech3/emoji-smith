"""Tests for EmojiSpecification value object."""

import pytest
from emojismith.domain.value_objects import EmojiSpecification
from emojismith.domain.exceptions import ValidationError
from shared.domain.value_objects import EmojiStylePreferences, StyleType


class TestEmojiSpecification:
    def test_prompt_construction(self) -> None:
        style = EmojiStylePreferences(style_type=StyleType.PIXEL_ART)
        spec = EmojiSpecification(
            context="Deploy failed", description="facepalm", style=style
        )
        assert spec.to_prompt().startswith("Deploy failed facepalm")
        assert "pixel_art" in spec.to_prompt()

    def test_prompt_construction_without_style(self) -> None:
        """Test prompt construction with empty style."""
        style = EmojiStylePreferences(style_type=StyleType.CARTOON)
        spec = EmojiSpecification(
            context="Deploy failed", description="facepalm", style=style
        )
        prompt = spec.to_prompt()
        assert "cartoon" in prompt

    def test_requires_fields(self) -> None:
        with pytest.raises(ValidationError):
            EmojiSpecification(context="", description="desc")
        with pytest.raises(ValidationError):
            EmojiSpecification(context="ctx", description="")
