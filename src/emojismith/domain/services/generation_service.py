"""Service for generating emoji images."""

from emojismith.domain.repositories.openai_repository import OpenAIRepository
from emojismith.domain.value_objects.emoji_specification import EmojiSpecification
from emojismith.domain.entities.generated_emoji import GeneratedEmoji
from emojismith.domain.services.prompt_service import AIPromptService
from emojismith.domain.repositories.image_processor import ImageProcessor
from emojismith.domain.services.emoji_validation_service import EmojiValidationService


class EmojiGenerationService:
    """Generate emojis using OpenAI and image processing."""

    def __init__(
        self,
        openai_repo: OpenAIRepository,
        image_processor: ImageProcessor,
        emoji_validator: EmojiValidationService,
    ) -> None:
        self._openai_repo = openai_repo
        self._prompt_service = AIPromptService(openai_repo)
        self._image_processor = image_processor
        self._emoji_validator = emoji_validator

    async def generate(self, spec: EmojiSpecification, name: str) -> GeneratedEmoji:
        prompt = await self._prompt_service.enhance(spec)
        raw_image = await self._openai_repo.generate_image(prompt)
        processed = self._image_processor.process(raw_image)
        return self._emoji_validator.validate_and_create_emoji(processed, name)
