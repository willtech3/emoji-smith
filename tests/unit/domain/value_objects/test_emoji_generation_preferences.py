"""Tests for EmojiGenerationPreferences value object."""

import pytest

from shared.domain.value_objects import (
    BackgroundType,
    EmojiGenerationPreferences,
    NumberOfImages,
    QualityLevel,
)


@pytest.mark.unit()
class TestBackgroundType:
    """Tests for BackgroundType enum."""

    def test_from_form_value_transparent(self):
        assert BackgroundType.from_form_value("transparent") == BackgroundType.TRANSPARENT

    def test_from_form_value_opaque(self):
        assert BackgroundType.from_form_value("opaque") == BackgroundType.OPAQUE

    def test_from_form_value_auto(self):
        assert BackgroundType.from_form_value("auto") == BackgroundType.AUTO

    def test_from_form_value_unknown_defaults_to_transparent(self):
        assert BackgroundType.from_form_value("unknown") == BackgroundType.TRANSPARENT


@pytest.mark.unit()
class TestQualityLevel:
    """Tests for QualityLevel enum."""

    def test_from_form_value_high(self):
        assert QualityLevel.from_form_value("high") == QualityLevel.HIGH

    def test_from_form_value_medium(self):
        assert QualityLevel.from_form_value("medium") == QualityLevel.MEDIUM

    def test_from_form_value_low(self):
        assert QualityLevel.from_form_value("low") == QualityLevel.LOW

    def test_from_form_value_auto(self):
        assert QualityLevel.from_form_value("auto") == QualityLevel.AUTO

    def test_from_form_value_unknown_defaults_to_high(self):
        assert QualityLevel.from_form_value("unknown") == QualityLevel.HIGH


@pytest.mark.unit()
class TestNumberOfImages:
    """Tests for NumberOfImages enum."""

    def test_from_form_value_one(self):
        assert NumberOfImages.from_form_value("1") == NumberOfImages.ONE

    def test_from_form_value_two(self):
        assert NumberOfImages.from_form_value("2") == NumberOfImages.TWO

    def test_from_form_value_four(self):
        assert NumberOfImages.from_form_value("4") == NumberOfImages.FOUR

    def test_from_form_value_unknown_defaults_to_one(self):
        assert NumberOfImages.from_form_value("5") == NumberOfImages.ONE

    def test_values_are_integers(self):
        assert NumberOfImages.ONE.value == 1
        assert NumberOfImages.TWO.value == 2
        assert NumberOfImages.FOUR.value == 4


@pytest.mark.unit()
class TestEmojiGenerationPreferences:
    """Tests for EmojiGenerationPreferences dataclass."""

    def test_default_values(self):
        prefs = EmojiGenerationPreferences()
        assert prefs.background == BackgroundType.TRANSPARENT
        assert prefs.quality == QualityLevel.HIGH
        assert prefs.num_images == NumberOfImages.ONE
        assert prefs.style_text == ""

    def test_from_form_values_with_all_fields(self):
        prefs = EmojiGenerationPreferences.from_form_values(
            background="opaque",
            quality="medium",
            num_images="4",
            style_text="cartoon, pixel art",
        )
        assert prefs.background == BackgroundType.OPAQUE
        assert prefs.quality == QualityLevel.MEDIUM
        assert prefs.num_images == NumberOfImages.FOUR
        assert prefs.style_text == "cartoon, pixel art"

    def test_from_form_values_with_defaults(self):
        prefs = EmojiGenerationPreferences.from_form_values()
        assert prefs.background == BackgroundType.TRANSPARENT
        assert prefs.quality == QualityLevel.HIGH
        assert prefs.num_images == NumberOfImages.ONE
        assert prefs.style_text == ""

    def test_to_dict_serialization(self):
        prefs = EmojiGenerationPreferences(
            background=BackgroundType.TRANSPARENT,
            quality=QualityLevel.HIGH,
            num_images=NumberOfImages.TWO,
            style_text="watercolor",
        )
        data = prefs.to_dict()
        assert data == {
            "background": "transparent",
            "quality": "high",
            "num_images": "2",
            "style_text": "watercolor",
        }

    def test_from_dict_deserialization(self):
        data = {
            "background": "opaque",
            "quality": "low",
            "num_images": "4",
            "style_text": "minimalist",
        }
        prefs = EmojiGenerationPreferences.from_dict(data)
        assert prefs.background == BackgroundType.OPAQUE
        assert prefs.quality == QualityLevel.LOW
        assert prefs.num_images == NumberOfImages.FOUR
        assert prefs.style_text == "minimalist"

    def test_from_dict_with_missing_fields_uses_defaults(self):
        prefs = EmojiGenerationPreferences.from_dict({})
        assert prefs.background == BackgroundType.TRANSPARENT
        assert prefs.quality == QualityLevel.HIGH
        assert prefs.num_images == NumberOfImages.ONE
        assert prefs.style_text == ""

    def test_from_dict_with_invalid_values_returns_defaults(self):
        prefs = EmojiGenerationPreferences.from_dict(
            {"background": "invalid", "quality": "invalid"}
        )
        # Should return defaults due to validation
        assert prefs.background == BackgroundType.TRANSPARENT

    def test_round_trip_serialization(self):
        original = EmojiGenerationPreferences(
            background=BackgroundType.AUTO,
            quality=QualityLevel.MEDIUM,
            num_images=NumberOfImages.TWO,
            style_text="3D render",
        )
        data = original.to_dict()
        restored = EmojiGenerationPreferences.from_dict(data)
        assert restored.background == original.background
        assert restored.quality == original.quality
        assert restored.num_images == original.num_images
        assert restored.style_text == original.style_text

    def test_to_prompt_fragment_with_style_text(self):
        prefs = EmojiGenerationPreferences(style_text="cartoon, bold")
        assert prefs.to_prompt_fragment() == "cartoon, bold"

    def test_to_prompt_fragment_with_empty_style(self):
        prefs = EmojiGenerationPreferences(style_text="")
        assert prefs.to_prompt_fragment() == ""

    def test_to_prompt_fragment_strips_whitespace(self):
        prefs = EmojiGenerationPreferences(style_text="  cartoon  ")
        assert prefs.to_prompt_fragment() == "cartoon"

    def test_get_background_prompt_suffix_transparent(self):
        prefs = EmojiGenerationPreferences(background=BackgroundType.TRANSPARENT)
        suffix = prefs.get_background_prompt_suffix()
        assert "transparent background" in suffix
        assert "bold shapes" in suffix
        assert "high contrast" in suffix
        assert "128x128" in suffix

    def test_get_background_prompt_suffix_opaque(self):
        prefs = EmojiGenerationPreferences(background=BackgroundType.OPAQUE)
        suffix = prefs.get_background_prompt_suffix()
        assert "transparent background" not in suffix
        assert "bold shapes" in suffix
        assert "high contrast" in suffix

    def test_is_immutable(self):
        prefs = EmojiGenerationPreferences()
        with pytest.raises(AttributeError):
            prefs.background = BackgroundType.OPAQUE  # type: ignore[misc]
