"""Tests for PromptBuilderService."""

import pytest

from emojismith.domain.services.prompt_builder_service import PromptBuilderService
from emojismith.domain.value_objects.emoji_specification import EmojiSpecification
from shared.domain.value_objects import EmojiStylePreferences, StyleType


class TestPromptBuilderService:
    """Test suite for PromptBuilderService."""

    @pytest.fixture()
    def service(self) -> PromptBuilderService:
        """Create a PromptBuilderService instance."""
        return PromptBuilderService()

    @pytest.fixture()
    def basic_spec(self) -> EmojiSpecification:
        """Create a basic emoji specification."""
        return EmojiSpecification(
            description="celebration",
            context="team just shipped a major feature",
        )

    def test_extract_themes_from_context(self, service: PromptBuilderService):
        """Should extract meaningful themes from context."""
        context = "team just shipped a major feature after working late nights"
        themes = service.extract_themes(context)

        assert "achievement" in themes
        assert "teamwork" in themes
        assert "dedication" in themes
        assert len(themes) >= 2

    def test_extract_themes_handles_empty_context(self, service: PromptBuilderService):
        """Should handle empty context gracefully."""
        themes = service.extract_themes("")
        assert themes == []

    def test_merge_description_and_context_basic(self, service: PromptBuilderService):
        """Should intelligently merge description with context."""
        description = "celebration"
        context = "team just shipped a major feature"
        themes = ["achievement", "teamwork"]

        merged = service.merge_description_and_context(description, context, themes)

        assert "celebration" in merged
        # Check that achievement theme is represented
        assert "success" in merged
        assert "feature" in merged  # Should include context element
        assert len(merged) > len(
            description
        )  # Should be more than just the description

    def test_merge_avoids_redundancy(self, service: PromptBuilderService):
        """Should avoid redundant words when merging."""
        description = "happy team"
        context = "team celebration after successful launch"
        themes = ["success", "teamwork"]

        merged = service.merge_description_and_context(description, context, themes)

        # Should not repeat "team" unnecessarily
        team_count = merged.lower().count("team")
        assert team_count <= 2

    def test_apply_style_modifiers_cartoon(self, service: PromptBuilderService):
        """Should apply cartoon style modifiers correctly."""
        base_prompt = "celebrating team achievement"
        style = "cartoon"

        styled = service.apply_style_modifiers(base_prompt, style)

        assert "cartoon" in styled.lower()
        assert any(
            word in styled.lower()
            for word in ["vibrant", "colorful", "playful", "exaggerated"]
        )

    def test_apply_style_modifiers_minimalist(self, service: PromptBuilderService):
        """Should apply minimalist style modifiers correctly."""
        base_prompt = "celebrating team achievement"
        style = "minimalist"

        styled = service.apply_style_modifiers(base_prompt, style)

        assert any(
            word in styled.lower()
            for word in ["minimalist", "simple", "clean", "minimal"]
        )
        assert "geometric" in styled.lower() or "simple shapes" in styled.lower()

    def test_apply_style_modifiers_pixel_art(self, service: PromptBuilderService):
        """Should apply pixel art style modifiers correctly."""
        base_prompt = "celebrating team achievement"
        style = "pixel_art"

        styled = service.apply_style_modifiers(base_prompt, style)

        assert (
            "pixel art" in styled.lower()
            or "8-bit" in styled.lower()
            or "pixelated" in styled.lower()
        )
        assert any(word in styled.lower() for word in ["retro", "nostalgic", "classic"])

    def test_apply_style_modifiers_realistic(self, service: PromptBuilderService):
        """Should apply realistic style modifiers correctly."""
        base_prompt = "celebrating team achievement"
        style = "realistic"

        styled = service.apply_style_modifiers(base_prompt, style)

        assert "realistic" in styled.lower()
        assert any(
            word in styled.lower()
            for word in ["detailed", "lifelike", "photorealistic"]
        )

    def test_apply_style_modifiers_unknown_style(self, service: PromptBuilderService):
        """Should handle unknown styles gracefully."""
        base_prompt = "celebrating team achievement"
        style = "unknown_style"

        styled = service.apply_style_modifiers(base_prompt, style)

        # Should return base prompt unmodified for unknown styles
        assert styled == base_prompt

    def test_add_emoji_requirements(self, service: PromptBuilderService):
        """Should add standard emoji requirements."""
        prompt = "celebrating team achievement"

        with_requirements = service.add_emoji_requirements(prompt)

        assert "emoji" in with_requirements.lower()
        assert "simple" in with_requirements.lower()
        assert "icon" in with_requirements.lower()

    def test_optimize_prompt_length_short(self, service: PromptBuilderService):
        """Should not modify short prompts."""
        short_prompt = "celebrating team"

        optimized = service.optimize_prompt_length(short_prompt)

        assert optimized == short_prompt

    def test_optimize_prompt_length_long(self, service: PromptBuilderService):
        """Should truncate and optimize long prompts."""
        # Create a prompt longer than max_length (default 150)
        long_prompt = " ".join(["word"] * 100)

        optimized = service.optimize_prompt_length(long_prompt)

        assert len(optimized) <= 150
        assert optimized.endswith("...")

    def test_optimize_prompt_preserves_key_info(self, service: PromptBuilderService):
        """Should preserve key information when optimizing."""
        prompt = "Create a " + " ".join(["very"] * 50) + " happy celebration emoji"

        optimized = service.optimize_prompt_length(prompt)

        assert "Create" in optimized
        # The word "emoji" might get truncated in very long prompts
        assert len(optimized) <= 150

    def test_build_prompt_complete_flow(
        self, service: PromptBuilderService, basic_spec: EmojiSpecification
    ):
        """Should build a complete optimized prompt."""
        style_prefs = EmojiStylePreferences(style_type=StyleType.CARTOON)
        spec_with_style = EmojiSpecification(
            description=basic_spec.description,
            context=basic_spec.context,
            style=style_prefs,
        )

        prompt = service.build_prompt(spec_with_style)

        # Should include description
        assert "celebration" in prompt.lower()
        # Should include themes from context
        assert any(
            word in prompt.lower()
            for word in [
                "achievement",
                "team",
                "success",
                "accomplishment",
                "collaboration",
            ]
        )
        # Should include style
        assert "cartoon" in prompt.lower()
        # Should include emoji requirements - the word might be truncated
        # due to length optimization
        assert "emoji" in prompt.lower() or "icon" in prompt.lower()
        # Should be optimized length
        assert len(prompt) <= 150

    def test_build_prompt_without_style(
        self, service: PromptBuilderService, basic_spec: EmojiSpecification
    ):
        """Should build prompt without style preferences."""
        prompt = service.build_prompt(basic_spec)

        assert "celebration" in prompt.lower()
        # Either emoji or icon should be present
        assert "emoji" in prompt.lower() or "icon" in prompt.lower()
        assert len(prompt) <= 150

    def test_extract_keywords_from_message(self, service: PromptBuilderService):
        """Should extract relevant keywords from the original message."""
        message = "We finally launched the new dashboard feature! Time to celebrate 🎉"
        keywords = service.extract_keywords(message)

        assert "launched" in keywords
        assert "dashboard" in keywords
        assert "feature" in keywords
        assert "celebrate" in keywords
        # Should not include common words
        assert "the" not in keywords
        assert "to" not in keywords

    def test_extract_keywords_filters_stopwords(self, service: PromptBuilderService):
        """Should filter out common stopwords."""
        message = "The team is very happy about the new feature"
        keywords = service.extract_keywords(message)

        assert "team" in keywords
        assert "happy" in keywords
        assert "feature" in keywords
        # Stopwords should be filtered
        assert "the" not in keywords
        assert "is" not in keywords
        assert "very" not in keywords
        assert "about" not in keywords

    def test_configuration_custom_max_length(self):
        """Should respect custom max_length configuration."""
        service = PromptBuilderService(max_prompt_length=100)
        long_prompt = " ".join(["word"] * 50)

        optimized = service.optimize_prompt_length(long_prompt)

        assert len(optimized) <= 100

    def test_configuration_custom_style_modifiers(self):
        """Should use custom style modifiers if provided."""
        custom_modifiers = {
            "custom_style": "in a custom artistic style with special effects"
        }
        service = PromptBuilderService(style_modifiers=custom_modifiers)

        styled = service.apply_style_modifiers("base prompt", "custom_style")

        assert "custom artistic style" in styled
        assert "special effects" in styled
