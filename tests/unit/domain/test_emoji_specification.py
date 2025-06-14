"""Tests for EmojiSpecification value object."""

import pytest
from emojismith.domain.value_objects import EmojiSpecification


class TestEmojiSpecification:
    def test_prompt_construction(self) -> None:
        spec = EmojiSpecification(
            context="Deploy failed", description="facepalm", style="pixel"
        )
        assert spec.to_prompt().startswith("Deploy failed facepalm")
        assert "pixel" in spec.to_prompt()

    def test_requires_fields(self) -> None:
        with pytest.raises(ValueError):
            EmojiSpecification(context="", description="desc")
        with pytest.raises(ValueError):
            EmojiSpecification(context="ctx", description="")
