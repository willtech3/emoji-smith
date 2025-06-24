"""Service for AI prompt enhancement."""

from typing import Optional, Dict
from emojismith.domain.repositories.openai_repository import OpenAIRepository
from emojismith.domain.value_objects.emoji_specification import EmojiSpecification
from emojismith.domain.services.style_template_manager import StyleTemplateManager


# Configuration constants
MAX_PROMPT_LENGTH = 1000


class AIPromptService:
    """Enhance prompts using OpenAI's chat models with fallback."""

    def __init__(
        self,
        openai_repo: OpenAIRepository,
        style_template_manager: StyleTemplateManager,
    ) -> None:
        self._repo = openai_repo
        self._style_template_manager = style_template_manager
        self._style_strategies: Dict[str, str] = {
            "professional": (
                "Create a professional, business-appropriate emoji that "
                "conveys {description} in a corporate setting."
            ),
            "playful": (
                "Design a fun, vibrant, and playful emoji showing "
                "{description} with energy and excitement."
            ),
            "minimal": (
                "Create a simple, clean, minimalist emoji representing "
                "{description} with essential elements only."
            ),
            "retro": (
                "Design a nostalgic, retro-style emoji showing "
                "{description} with vintage aesthetics."
            ),
        }

    async def enhance(self, spec: EmojiSpecification) -> str:
        """Enhance prompt using style templates and AI enhancement."""
        # Apply style template if available
        if spec.style and hasattr(spec.style, "style_type"):
            enhanced_prompt = self._style_template_manager.apply_style_template(
                base_prompt=spec.description, style_type=spec.style.style_type
            )
            # Add context to the enhanced prompt
            if spec.context:
                enhanced_prompt += f" Context: {spec.context}"
        else:
            # Fallback to AI enhancement
            enhanced_prompt = await self._repo.enhance_prompt(
                spec.context, spec.description
            )

        return enhanced_prompt

    async def build_prompt(
        self, spec: EmojiSpecification, style: Optional[str] = None
    ) -> str:
        """Build enhanced prompt with style strategies and context enrichment."""
        base_prompt = spec.to_prompt()

        # Apply style strategy if specified
        if style and style in self._style_strategies:
            style_template = self._style_strategies[style]
            base_prompt = style_template.format(description=spec.description)
            base_prompt += f" Context: {spec.context}"

        # Enrich based on context patterns
        enriched = self._enrich_context(base_prompt, spec.context)

        # Handle edge cases
        enriched = self._handle_edge_cases(enriched)

        return enriched

    def _enrich_context(self, prompt: str, context: str) -> str:
        """Enrich prompt based on detected context patterns."""
        context_lower = context.lower()

        # Detect deployment/production context
        if any(word in context_lower for word in ["deploy", "production", "release"]):
            if "friday" in context_lower:
                prompt += (
                    " Include subtle elements suggesting risk or careful consideration."
                )
            else:
                prompt += " Include elements suggesting deployment or release activity."

        return prompt

    def _handle_edge_cases(self, prompt: str) -> str:
        """Handle edge cases like length limits."""
        # Truncate if too long
        if len(prompt) > MAX_PROMPT_LENGTH:
            prompt = prompt[: MAX_PROMPT_LENGTH - 3] + "..."

        return prompt
