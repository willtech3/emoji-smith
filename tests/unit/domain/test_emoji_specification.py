"""Tests for EmojiSpecification value object."""

import pytest

from emojismith.domain.exceptions import ValidationError
from emojismith.domain.value_objects import EmojiSpecification
from shared.domain.value_objects import EmojiStylePreferences, StyleType


@pytest.mark.unit()
class TestEmojiSpecification:
    def test_emoji_specification_to_prompt_includes_style(self) -> None:
        style = EmojiStylePreferences(style_type=StyleType.PIXEL_ART)
        spec = EmojiSpecification(
            context="Deploy failed", description="facepalm", style=style
        )
        assert spec.to_prompt().startswith("Deploy failed facepalm")
        assert "pixel_art" in spec.to_prompt()

    def test_emoji_specification_to_prompt_with_default_style(self) -> None:
        """Test prompt construction with empty style."""
        style = EmojiStylePreferences(style_type=StyleType.CARTOON)
        spec = EmojiSpecification(
            context="Deploy failed", description="facepalm", style=style
        )
        prompt = spec.to_prompt()
        assert "cartoon" in prompt

    def test_emoji_specification_missing_description_raises_error(self) -> None:
        """Test that empty description still raises a validation error."""
        with pytest.raises(ValidationError):
            EmojiSpecification(context="ctx", description="")

    def test_emoji_specification_empty_context_allowed(self) -> None:
        """Test that empty context is allowed for messages without text."""
        spec = EmojiSpecification(context="", description="thumbs up emoji")
        assert spec.to_prompt().startswith("thumbs up emoji")

    def test_emoji_specification_to_prompt_with_empty_context(self) -> None:
        """Test prompt construction with empty context uses only description."""
        style = EmojiStylePreferences(style_type=StyleType.PIXEL_ART)
        spec = EmojiSpecification(context="", description="facepalm", style=style)
        prompt = spec.to_prompt()
        assert prompt.startswith("facepalm")
        assert "pixel_art" in prompt

