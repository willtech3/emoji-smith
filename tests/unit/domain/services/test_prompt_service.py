"""Tests for AIPromptService and EmojiGenerationService."""

import pytest
from unittest.mock import AsyncMock
from io import BytesIO
from PIL import Image
from emojismith.domain.value_objects import EmojiSpecification
from emojismith.domain.services import AIPromptService, EmojiGenerationService
from emojismith.domain.entities.generated_emoji import GeneratedEmoji
from emojismith.domain.repositories.image_processor import ImageProcessor


class DummyProcessor(ImageProcessor):
    def process(self, image_data: bytes) -> bytes:  # type: ignore[override]
        return image_data


@pytest.mark.asyncio
async def test_prompt_service_enhances() -> None:
    repo = AsyncMock()
    repo.enhance_prompt.return_value = "enhanced"
    spec = EmojiSpecification(context="ctx", description="desc")
    service = AIPromptService(repo)
    result = await service.enhance(spec)
    assert result == "enhanced"


@pytest.mark.asyncio
async def test_generation_service_flow() -> None:
    repo = AsyncMock()
    repo.enhance_prompt.return_value = "good"
    img = Image.new("RGBA", (128, 128), "red")
    bio = BytesIO()
    img.save(bio, format="PNG")
    repo.generate_image.return_value = bio.getvalue()
    processor = DummyProcessor()
    service = EmojiGenerationService(repo, processor)
    spec = EmojiSpecification(context="ctx", description="desc")
    emoji = await service.generate(spec, "name")
    assert isinstance(emoji, GeneratedEmoji)
