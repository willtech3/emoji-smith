"""Use case for building optimized prompts for emoji generation."""

import logging

from emojismith.domain.repositories.openai_repository import OpenAIRepository
from emojismith.domain.services.description_quality_analyzer import (
    DescriptionQualityAnalyzer,
)
from emojismith.domain.services.prompt_builder_service import PromptBuilderService
from emojismith.domain.value_objects.emoji_specification import EmojiSpecification


class BuildPromptUseCase:
    """Orchestrates prompt building with optional AI enhancement."""

    _logger = logging.getLogger(__name__)

    def __init__(
        self,
        openai_repository: OpenAIRepository,
        prompt_builder_service: PromptBuilderService | None = None,
        description_quality_analyzer: DescriptionQualityAnalyzer | None = None,
    ) -> None:
        """Initialize the use case.

        Args:
            openai_repository: Repository for OpenAI operations
            prompt_builder_service: Service for building prompts
                (creates default if not provided)
            description_quality_analyzer: Service for analyzing description quality
                (creates default if not provided)
        """
        self._openai_repository = openai_repository
        self._prompt_builder_service = prompt_builder_service or PromptBuilderService()
        self._description_quality_analyzer = (
            description_quality_analyzer or DescriptionQualityAnalyzer()
        )

    async def build_prompt(
        self,
        spec: EmojiSpecification,
        enhance: bool = True,
        style_override: str | None = None,
    ) -> str:
        """Build an optimized prompt for emoji generation.

        Args:
            spec: The emoji specification containing description, context, and style
            enhance: Whether to enhance the prompt using AI (default: True)
            style_override: Optional style to override the specification's style

        Returns:
            An optimized prompt string ready for gpt-image-1
        """
        # If style override is provided, create a new spec with that style
        if style_override:
            # Import here to avoid circular dependency
            from shared.domain.value_objects import EmojiStylePreferences, StyleType

            # Map string to StyleType
            style_mapping = {
                "cartoon": StyleType.CARTOON,
                "realistic": StyleType.REALISTIC,
                "minimalist": StyleType.MINIMALIST,
                "pixel_art": StyleType.PIXEL_ART,
            }

            if style_override in style_mapping:
                style_prefs = EmojiStylePreferences(
                    style_type=style_mapping[style_override]
                )
                spec = EmojiSpecification(
                    description=spec.description,
                    context=spec.context,
                    style=style_prefs,
                )

        # Check description quality and decide on strategy
        quality_score, issues = self._description_quality_analyzer.analyze_description(
            spec.description
        )

        # If description is poor quality, use fallback generation
        if self._description_quality_analyzer.is_poor_quality(spec.description):
            self._logger.info(
                f"Using fallback prompt generation due to poor description quality. "
                f"Score: {quality_score:.2f}, Issues: {', '.join(issues)}"
            )

            # Generate a better prompt using context
            fallback_description = (
                self._description_quality_analyzer.generate_fallback_prompt(
                    spec.context, spec.description
                )
            )

            # Create a new spec with the improved description
            improved_spec = EmojiSpecification(
                description=fallback_description,
                context=spec.context,
                style=spec.style,
            )

            # Build prompt with improved description
            base_prompt = self._prompt_builder_service.build_prompt(improved_spec)
        else:
            # Description is good enough, use it as-is
            base_prompt = self._prompt_builder_service.build_prompt(spec)

        # If enhancement is requested, use OpenAI to enhance the prompt
        if enhance:
            try:
                # The enhance_prompt method expects (context, description)
                # We'll pass the full built prompt as the description
                # since it already includes context
                enhanced_prompt = await self._openai_repository.enhance_prompt(
                    spec.context, base_prompt
                )
                return enhanced_prompt
            except Exception as e:
                self._logger.warning(
                    f"Failed to enhance prompt with AI, "
                    f"falling back to base prompt: {e}"
                )
                return base_prompt

        return base_prompt
