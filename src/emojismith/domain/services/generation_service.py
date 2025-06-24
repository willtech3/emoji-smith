"""Service for generating emoji images."""

from emojismith.domain.repositories.openai_repository import OpenAIRepository
from emojismith.domain.entities.generated_emoji import GeneratedEmoji
from emojismith.domain.repositories.image_processor import ImageProcessor
from emojismith.domain.services.emoji_validation_service import EmojiValidationService


class EmojiGenerationService:
    """Generate emojis using OpenAI and image processing."""

    def __init__(
        self,
        openai_repo: OpenAIRepository,
        image_processor: ImageProcessor,
        emoji_validator: EmojiValidationService,
        style_template_manager: StyleTemplateManager,
    ) -> None:
        self._openai_repo = openai_repo
        self._image_processor = image_processor
        self._emoji_validator = emoji_validator

    async def generate_from_prompt(self, prompt: str, name: str) -> GeneratedEmoji:
        """Generate emoji from a ready-to-use prompt.

        Args:
            prompt: The optimized and enhanced prompt for DALL-E
            name: The name for the generated emoji

        Returns:
            The generated and validated emoji
        """
        raw_image = await self._openai_repo.generate_image(prompt)
        processed = self._image_processor.process(raw_image)
        return self._emoji_validator.validate_and_create_emoji(processed, name)
