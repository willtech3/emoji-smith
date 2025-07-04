import pytest

from shared.domain.value_objects import EmojiStylePreferences


@pytest.mark.unit()
class TestEmojiStylePreferences:
    def test_to_prompt_fragment(self) -> None:
        prefs = EmojiStylePreferences()
        fragment = prefs.to_prompt_fragment()
        assert "cartoon" in fragment
        assert "fun" in fragment

    def test_from_form_values(self) -> None:
        prefs = EmojiStylePreferences.from_form_values(
            style_type="pixel_art",
            color_scheme="bright",
            detail_level="detailed",
            tone="expressive",
        )
        assert prefs.style_type.value == "pixel_art"
        assert prefs.color_scheme.value == "bright"
        assert prefs.detail_level.value == "detailed"
        assert prefs.tone.value == "expressive"
