"""Service for generating emoji images."""

from emojismith.domain.repositories.openai_repository import OpenAIRepository
from emojismith.domain.value_objects.emoji_specification import EmojiSpecification
from emojismith.domain.entities.generated_emoji import GeneratedEmoji
from emojismith.domain.services.prompt_service import AIPromptService
from emojismith.domain.repositories.image_processor import ImageProcessor


class EmojiGenerationService:
    """Generate emojis using OpenAI and image processing."""

    def __init__(
        self,
        openai_repo: OpenAIRepository,
        image_processor: ImageProcessor,
    ) -> None:
        self._openai_repo = openai_repo
        self._prompt_service = AIPromptService(openai_repo)
        self._image_processor = image_processor

    async def generate(self, spec: EmojiSpecification, name: str) -> GeneratedEmoji:
        prompt = await self._prompt_service.enhance(spec)
        raw_image = await self._openai_repo.generate_image(prompt)
        processed = self._image_processor.process(raw_image)
        return GeneratedEmoji(image_data=processed, name=name)
