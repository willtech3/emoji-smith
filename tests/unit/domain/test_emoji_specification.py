"""Tests for EmojiSpecification value object."""

import pytest
from emojismith.domain.value_objects import EmojiSpecification
from shared.domain.value_objects import StylePreferences


class TestEmojiSpecification:
    def test_prompt_construction(self) -> None:
        prefs = StylePreferences(
            style="pixel", color_scheme="bright", detail_level="simple", tone="fun"
        )
        spec = EmojiSpecification(
            context="Deploy failed", description="facepalm", style_preferences=prefs
        )
        assert spec.to_prompt().startswith("Deploy failed facepalm")
        assert "pixel" in spec.to_prompt()

    def test_prompt_construction_without_style(self) -> None:
        """Test prompt construction with empty style."""
        prefs = StylePreferences(style="", color_scheme="", detail_level="", tone="")
        spec = EmojiSpecification(
            context="Deploy failed", description="facepalm", style_preferences=prefs
        )
        prompt = spec.to_prompt()
        assert prompt == "Deploy failed facepalm"
        assert "style" not in prompt

    def test_requires_fields(self) -> None:
        with pytest.raises(ValueError):
            EmojiSpecification(
                context="",
                description="desc",
                style_preferences=StylePreferences(
                    style="pixel",
                    color_scheme="bright",
                    detail_level="simple",
                    tone="fun",
                ),
            )
        with pytest.raises(ValueError):
            EmojiSpecification(
                context="ctx",
                description="",
                style_preferences=StylePreferences(
                    style="pixel",
                    color_scheme="bright",
                    detail_level="simple",
                    tone="fun",
                ),
            )
