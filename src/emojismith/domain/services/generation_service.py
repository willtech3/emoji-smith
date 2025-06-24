"""Service for generating emoji images."""

from emojismith.domain.repositories.openai_repository import OpenAIRepository
from emojismith.domain.value_objects.emoji_specification import EmojiSpecification
from emojismith.domain.entities.generated_emoji import GeneratedEmoji
from emojismith.domain.services.prompt_builder_service import PromptBuilderService
from emojismith.domain.repositories.image_processor import ImageProcessor
from emojismith.domain.services.emoji_validation_service import EmojiValidationService


class EmojiGenerationService:
    """Generate emojis using OpenAI and image processing."""

    def __init__(
        self,
        openai_repo: OpenAIRepository,
        image_processor: ImageProcessor,
        emoji_validator: EmojiValidationService,
        prompt_builder_service: PromptBuilderService | None = None,
    ) -> None:
        self._openai_repo = openai_repo
        self._prompt_builder_service = prompt_builder_service or PromptBuilderService()
        self._image_processor = image_processor
        self._emoji_validator = emoji_validator

    async def generate(self, spec: EmojiSpecification, name: str) -> GeneratedEmoji:
        # Build optimized prompt using the new service
        prompt = self._prompt_builder_service.build_prompt(spec)
        # Optionally enhance with AI (keeping existing behavior)
        enhanced_prompt = await self._openai_repo.enhance_prompt(spec.context, prompt)
        raw_image = await self._openai_repo.generate_image(enhanced_prompt)
        processed = self._image_processor.process(raw_image)
        return self._emoji_validator.validate_and_create_emoji(processed, name)
