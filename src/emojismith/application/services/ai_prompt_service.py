"""Service for AI prompt enhancement."""

from typing import Optional
from emojismith.domain.repositories.openai_repository import OpenAIRepository
from emojismith.domain.value_objects.emoji_specification import EmojiSpecification
from emojismith.domain.services.style_template_manager import (
    StyleTemplateManager,
    MAX_PROMPT_LENGTH,
)


class AIPromptService:
    """Enhance prompts using OpenAI's chat models with fallback."""

    def __init__(
        self,
        openai_repo: OpenAIRepository,
        style_template_manager: StyleTemplateManager,
    ) -> None:
        self._repo = openai_repo
        self._style_template_manager = style_template_manager

    async def enhance(self, spec: EmojiSpecification) -> str:
        return await self._repo.enhance_prompt(spec.context, spec.description)

    async def build_prompt(
        self, spec: EmojiSpecification, style: Optional[str] = None
    ) -> str:
        """Build enhanced prompt with style strategies and context enrichment."""
        base_prompt = spec.to_prompt()

        # Apply style template if specified
        if style:
            base_prompt = self._style_template_manager.apply_style_template(
                base_prompt, style
            )

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
