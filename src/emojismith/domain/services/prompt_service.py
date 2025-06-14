"""Service for AI prompt enhancement."""

from emojismith.domain.repositories.openai_repository import OpenAIRepository
from emojismith.domain.value_objects.emoji_specification import EmojiSpecification


class AIPromptService:
    """Enhance prompts using OpenAI chat models with fallback."""

    def __init__(self, openai_repo: OpenAIRepository) -> None:
        self._repo = openai_repo

    async def enhance(self, spec: EmojiSpecification) -> str:
        return await self._repo.enhance_prompt(spec.context, spec.description)
