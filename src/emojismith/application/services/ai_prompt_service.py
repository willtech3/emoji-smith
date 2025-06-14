"""Service orchestrating AI prompt optimisation and image generation."""

from emojismith.domain.value_objects import EmojiSpecification, GeneratedEmoji
from emojismith.domain.repositories.openai_repository import OpenAIRepository


class AIPromptService:
    """Generate emojis using OpenAI services."""

    def __init__(self, ai_repo: OpenAIRepository) -> None:
        self._ai_repo = ai_repo

    async def generate_emoji(self, spec: EmojiSpecification) -> GeneratedEmoji:
        """Generate an emoji based on the specification."""
        prompt = await self._ai_repo.optimize_prompt(
            context=spec.context,
            description=spec.description,
        )
        image_bytes = await self._ai_repo.generate_image(prompt=prompt)
        return GeneratedEmoji(name="generated", image_data=image_bytes)
