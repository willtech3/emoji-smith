"""Tests for StyleTemplate value object."""

import pytest
from emojismith.domain.value_objects.style_template import StyleTemplate
from shared.domain.value_objects import StyleType


class TestStyleTemplate:
    """Test StyleTemplate value object behavior."""

    def test_style_template_creation(self):
        """StyleTemplate should be created with all required attributes."""
        template = StyleTemplate(
            style_type=StyleType.CARTOON,
            prefix="Create a cartoon emoji with",
            suffix="in animated style",
            keywords=("vibrant", "playful", "colorful"),
            avoid_words=("realistic", "photo"),
        )

        assert template.style_type == StyleType.CARTOON
        assert template.prefix == "Create a cartoon emoji with"
        assert template.suffix == "in animated style"
        assert template.keywords == ("vibrant", "playful", "colorful")
        assert template.avoid_words == ("realistic", "photo")

    def test_style_template_is_immutable(self):
        """StyleTemplate should be immutable (frozen dataclass)."""
        template = StyleTemplate(
            style_type=StyleType.MINIMALIST,
            prefix="Create a minimal",
            suffix="with simple design",
            keywords=("simple", "clean"),
            avoid_words=("complex",),
        )

        with pytest.raises(AttributeError):
            template.prefix = "Modified prefix"

        with pytest.raises(AttributeError):
            template.keywords = template.keywords + ("new keyword",)

    def test_style_template_equality(self):
        """StyleTemplates with same values should be equal."""
        template1 = StyleTemplate(
            style_type=StyleType.PIXEL_ART,
            prefix="Create pixel art",
            suffix="in 8-bit style",
            keywords=("pixelated", "retro"),
            avoid_words=("smooth",),
        )

        template2 = StyleTemplate(
            style_type=StyleType.PIXEL_ART,
            prefix="Create pixel art",
            suffix="in 8-bit style",
            keywords=("pixelated", "retro"),
            avoid_words=("smooth",),
        )

        assert template1 == template2
        assert hash(template1) == hash(template2)

    def test_style_template_inequality(self):
        """StyleTemplates with different values should not be equal."""
        template1 = StyleTemplate(
            style_type=StyleType.REALISTIC,
            prefix="Create realistic",
            suffix="with details",
            keywords=("detailed",),
            avoid_words=("cartoon",),
        )

        template2 = StyleTemplate(
            style_type=StyleType.REALISTIC,
            prefix="Create realistic",
            suffix="with details",
            keywords=("photorealistic",),  # Different keyword
            avoid_words=("cartoon",),
        )

        assert template1 != template2

    def test_style_template_with_empty_keywords(self):
        """StyleTemplate should accept empty keyword list."""
        template = StyleTemplate(
            style_type=StyleType.CARTOON,
            prefix="Create emoji",
            suffix="in style",
            keywords=(),
            avoid_words=(),
        )

        assert template.keywords == ()
        assert template.avoid_words == ()

    def test_format_prompt_basic(self):
        """Format prompt should combine prefix, content, and suffix."""
        template = StyleTemplate(
            style_type=StyleType.CARTOON,
            prefix="Create a cartoon emoji showing",
            suffix="with vibrant colors",
            keywords=("colorful",),
            avoid_words=(),
        )

        result = template.format_prompt("a happy cat")

        assert (
            result == "Create a cartoon emoji showing a happy cat with vibrant colors"
        )

    def test_format_prompt_with_empty_content(self):
        """Format prompt should handle empty content gracefully."""
        template = StyleTemplate(
            style_type=StyleType.MINIMALIST,
            prefix="Create a minimal emoji",
            suffix="with clean design",
            keywords=(),
            avoid_words=(),
        )

        result = template.format_prompt("")

        assert result == "Create a minimal emoji  with clean design"

    def test_has_keyword(self):
        """Has keyword should check case-insensitively."""
        template = StyleTemplate(
            style_type=StyleType.PIXEL_ART,
            prefix="Create",
            suffix="style",
            keywords=("Pixelated", "RETRO", "8-bit"),
            avoid_words=(),
        )

        assert template.has_keyword("pixelated")
        assert template.has_keyword("PIXELATED")
        assert template.has_keyword("retro")
        assert template.has_keyword("8-bit")
        assert not template.has_keyword("smooth")

    def test_should_avoid_word(self):
        """Should avoid word should check case-insensitively."""
        template = StyleTemplate(
            style_type=StyleType.CARTOON,
            prefix="Create",
            suffix="style",
            keywords=(),
            avoid_words=("Realistic", "PHOTO", "detailed"),
        )

        assert template.should_avoid_word("realistic")
        assert template.should_avoid_word("REALISTIC")
        assert template.should_avoid_word("photo")
        assert template.should_avoid_word("detailed")
        assert not template.should_avoid_word("cartoon")
