"""Service for generating emoji images."""

from emojismith.domain.entities.generated_emoji import GeneratedEmoji
from emojismith.domain.repositories.image_generation_repository import (
    ImageGenerationRepository,
)
from emojismith.domain.repositories.image_processor import ImageProcessor
from emojismith.domain.services.emoji_validation_service import EmojiValidationService
from emojismith.domain.services.style_template_manager import StyleTemplateManager


class EmojiGenerationService:
    """Generate emojis using a pluggable image generation provider."""

    def __init__(
        self,
        image_generator: ImageGenerationRepository,
        image_processor: ImageProcessor,
        emoji_validator: EmojiValidationService,
        style_template_manager: StyleTemplateManager,
    ) -> None:
        self._image_generator = image_generator
        self._image_processor = image_processor
        self._emoji_validator = emoji_validator
        self._style_template_manager = style_template_manager

    async def generate_from_prompt(self, prompt: str, name: str) -> GeneratedEmoji:
        """Generate emoji from a ready-to-use prompt.

        Args:
            prompt: The optimized and enhanced prompt for the image model
            name: The name for the generated emoji

        Returns:
            The generated and validated emoji
        """
        images = await self._image_generator.generate_image(prompt)
        if not images:
            raise ValueError("Image generation returned no images")
        raw_image = images[0]  # Use first generated image
        processed = self._image_processor.process(raw_image)
        return self._emoji_validator.validate_and_create_emoji(processed, name)
