"""Tests for StyleTemplateManager in domain layer."""

import pytest

from emojismith.domain.services.style_template_manager import StyleTemplateManager
from emojismith.domain.value_objects.style_template import StyleTemplate
from emojismith.infrastructure.repositories.style_template_config_repository import (
    StyleTemplateConfigRepository,
)
from shared.domain.value_objects import StyleType


class TestStyleTemplateManager:
    """Test StyleTemplateManager behavior."""

    @pytest.fixture()
    def repository(self):
        """Create style template repository."""
        return StyleTemplateConfigRepository()

    @pytest.fixture()
    def manager(self, repository):
        """Create StyleTemplateManager instance."""
        return StyleTemplateManager(repository)

    def test_manager_has_templates_for_all_style_types(self, manager):
        """Manager should have templates for all defined style types."""

        for style_type in StyleType:
            template = manager.get_template(style_type)
            assert template is not None
            assert isinstance(template, StyleTemplate)
            assert template.style_type == style_type

    def test_cartoon_style_template_configuration(self, manager):
        """Cartoon style should have appropriate template configuration."""
        template = manager.get_template(StyleType.CARTOON)

        assert template.prefix == "Create a vibrant, cartoon-style emoji with"
        assert (
            template.suffix
            == "in a fun, animated style with bold colors and expressive features"
        )
        assert "vibrant" in template.keywords
        assert "playful" in template.keywords
        assert "colorful" in template.keywords
        assert "realistic" in template.avoid_words
        assert "photographic" in template.avoid_words

    def test_pixel_art_style_template_configuration(self, manager):
        """Pixel art style should have appropriate template configuration."""
        template = manager.get_template(StyleType.PIXEL_ART)

        assert template.prefix == "Design a retro pixel art emoji showing"
        assert (
            template.suffix
            == "in 8-bit or 16-bit pixel art style with clean pixelated edges"
        )
        assert "8-bit" in template.keywords
        assert "pixelated" in template.keywords
        assert "retro" in template.keywords
        assert "smooth" in template.avoid_words
        assert "realistic" in template.avoid_words

    def test_minimalist_style_template_configuration(self, manager):
        """Minimalist style should have appropriate template configuration."""
        template = manager.get_template(StyleType.MINIMALIST)

        assert template.prefix == "Create a simple, minimalist emoji depicting"
        assert (
            template.suffix
            == "using clean lines, minimal details, and essential elements only"
        )
        assert "simple" in template.keywords
        assert "clean" in template.keywords
        assert "minimal" in template.keywords
        assert "complex" in template.avoid_words
        assert "detailed" in template.avoid_words

    def test_realistic_style_template_configuration(self, manager):
        """Realistic style should have appropriate template configuration."""
        template = manager.get_template(StyleType.REALISTIC)

        assert template.prefix == "Generate a realistic, detailed emoji showing"
        assert template.suffix == "with photorealistic details and natural textures"
        assert "realistic" in template.keywords
        assert "detailed" in template.keywords
        assert "photorealistic" in template.keywords
        assert "cartoon" in template.avoid_words
        assert "abstract" in template.avoid_words

    def test_apply_style_template_basic_prompt(self, manager):
        """Apply style template should enhance basic prompts correctly."""

        result = manager.apply_style_template(
            base_prompt="a happy cat", style_type=StyleType.CARTOON
        )

        assert result.startswith("Create a vibrant, cartoon-style emoji with")
        assert "a happy cat" in result
        assert result.endswith(
            "in a fun, animated style with bold colors and expressive features"
        )
        assert "vibrant" in result or "playful" in result  # Keywords should be added

    def test_apply_style_template_avoids_redundant_keywords(self, manager):
        """Apply style template should not add keywords already in prompt."""

        result = manager.apply_style_template(
            base_prompt="a vibrant colorful happy cat", style_type=StyleType.CARTOON
        )

        # The template prefix contains "vibrant", and the prompt contains "vibrant"
        # So we expect 2 occurrences total (one from template, one from prompt)
        # But "colorful" should only appear once (from the prompt)
        assert result.count("vibrant") == 2  # One in template prefix, one in prompt
        assert result.count("colorful") == 1  # Only in prompt
        assert "playful" in result  # Should be added as a missing keyword

    def test_apply_style_template_removes_avoid_words(self, manager):
        """Apply style template should remove words that conflict with style."""

        result = manager.apply_style_template(
            base_prompt="a realistic photographic cat", style_type=StyleType.CARTOON
        )

        # Should remove "realistic" and "photographic" for cartoon style
        assert "realistic" not in result
        assert "photographic" not in result
        assert "a cat" in result  # Core subject should remain

    def test_apply_style_template_preserves_context(self, manager):
        """Apply style template should preserve important context."""

        result = manager.apply_style_template(
            base_prompt="a cat wearing a party hat celebrating a birthday",
            style_type=StyleType.MINIMALIST,
        )

        # All context should be preserved
        assert "cat" in result
        assert "party hat" in result
        assert "birthday" in result

    def test_apply_style_template_handles_empty_prompt(self, manager):
        """Apply style template should handle empty prompts gracefully."""

        result = manager.apply_style_template(
            base_prompt="", style_type=StyleType.PIXEL_ART
        )

        assert result.startswith("Design a retro pixel art emoji showing")
        assert result.endswith(
            "in 8-bit or 16-bit pixel art style with clean pixelated edges"
        )

    def test_get_all_templates_returns_all_styles(self, manager):
        """Get all templates should return templates for all style types."""
        templates = manager.get_all_templates()

        assert len(templates) == len(StyleType)
        style_types = {template.style_type for template in templates.values()}
        assert style_types == set(StyleType)

    def test_templates_are_immutable(self, manager):
        """Style templates should be immutable value objects."""
        template = manager.get_template(StyleType.CARTOON)

        # Verify template is frozen (immutable)
        with pytest.raises(AttributeError):
            template.prefix = "Modified prefix"

    def test_apply_style_template_with_complex_prompt(self, manager):
        """Apply style template should handle complex prompts with punctuation."""

        result = manager.apply_style_template(
            base_prompt='a developer saying "I deployed on Friday!"',
            style_type=StyleType.PIXEL_ART,
        )

        assert 'a developer saying "I deployed on Friday!"' in result
        assert "8-bit" in result or "pixelated" in result
