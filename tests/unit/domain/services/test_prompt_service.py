"""Tests for AIPromptService and EmojiGenerationService."""

import pytest
from unittest.mock import AsyncMock, Mock
from io import BytesIO
from PIL import Image
from emojismith.domain.value_objects import EmojiSpecification
from emojismith.domain.services import AIPromptService, EmojiGenerationService
from emojismith.domain.services.emoji_validation_service import EmojiValidationService
from emojismith.domain.entities.generated_emoji import GeneratedEmoji
from emojismith.domain.repositories.image_processor import ImageProcessor


class DummyProcessor(ImageProcessor):
    def process(self, image_data: bytes) -> bytes:  # type: ignore[override]
        return image_data


@pytest.mark.asyncio
async def test_prompt_service_when_spec_valid_returns_enhanced_prompt() -> None:
    repo = AsyncMock()
    repo.enhance_prompt.return_value = "enhanced"
    spec = EmojiSpecification(context="ctx", description="desc")
    service = AIPromptService(repo)
    result = await service.enhance(spec)
    assert result == "enhanced"
    repo.enhance_prompt.assert_called_once()


@pytest.mark.asyncio
async def test_emoji_generation_service_when_spec_valid_returns_entity() -> None:
    repo = AsyncMock()
    repo.enhance_prompt.return_value = "good"
    img = Image.new("RGBA", (128, 128), "red")
    bio = BytesIO()
    img.save(bio, format="PNG")
    image_data = bio.getvalue()
    repo.generate_image.return_value = image_data
    processor = DummyProcessor()

    # Create mock validation service that returns valid GeneratedEmoji
    mock_validator = Mock()
    validation_service = EmojiValidationService(mock_validator)
    mock_validator.validate_emoji_format.return_value = None

    service = EmojiGenerationService(repo, processor, validation_service)
    spec = EmojiSpecification(context="ctx", description="desc")
    emoji = await service.generate(spec, "name")
    assert isinstance(emoji, GeneratedEmoji)
    assert emoji.name == "name"
    repo.enhance_prompt.assert_called_once()
    repo.generate_image.assert_called_once()
    mock_validator.validate_emoji_format.assert_called_once_with(image_data)
