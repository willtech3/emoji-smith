"""Service for AI prompt enhancement."""

from typing import Optional, Dict
from emojismith.domain.repositories.openai_repository import OpenAIRepository
from emojismith.domain.value_objects.emoji_specification import EmojiSpecification


class AIPromptService:
    """Enhance prompts using OpenAI's chat models with fallback."""

    def __init__(self, openai_repo: OpenAIRepository) -> None:
        self._repo = openai_repo
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
        return await self._repo.enhance_prompt(spec.context, spec.description)

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
        """Handle edge cases like length limits and sanitization."""
        # Truncate if too long
        if len(prompt) > 1000:
            prompt = prompt[:997] + "..."

        # Basic sanitization
        prompt = prompt.replace("<script>", "").replace("</script>", "")
        prompt = prompt.replace("<", "&lt;").replace(">", "&gt;")

        return prompt
