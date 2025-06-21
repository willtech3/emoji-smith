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
async def test_prompt_service_enhances() -> None:
    repo = AsyncMock()
    repo.enhance_prompt.return_value = "enhanced"
    spec = EmojiSpecification(context="ctx", description="desc")
    service = AIPromptService(repo)
    result = await service.enhance(spec)
    assert result == "enhanced"
    repo.enhance_prompt.assert_called_once()


@pytest.mark.asyncio
async def test_prompt_service_build_with_style_strategy() -> None:
    """Service should apply style-specific prompt building strategy."""
    repo = AsyncMock()
    repo.enhance_prompt.return_value = "enhanced prompt"

    spec = EmojiSpecification(context="discussing code", description="facepalm")
    service = AIPromptService(repo)

    # Build prompt with professional style
    professional_prompt = await service.build_prompt(spec, style="professional")
    assert "professional" in professional_prompt
    assert "business-appropriate" in professional_prompt

    # Build prompt with playful style
    playful_prompt = await service.build_prompt(spec, style="playful")
    assert "fun" in playful_prompt
    assert "vibrant" in playful_prompt


@pytest.mark.asyncio
async def test_prompt_service_build_with_context_enrichment() -> None:
    """Service should enrich prompts based on message context."""
    repo = AsyncMock()
    service = AIPromptService(repo)

    spec = EmojiSpecification(
        context="Just deployed to production on Friday afternoon",
        description="nervous laugh",
    )

    prompt = await service.build_prompt(spec)

    # Should detect risky deployment context
    assert "deploy" in prompt.lower()  # Can match "deployed" or "deployment"
    assert "risk" in prompt.lower() or "careful" in prompt.lower()


@pytest.mark.asyncio
async def test_prompt_service_handles_edge_cases() -> None:
    """Service should handle edge cases gracefully."""
    repo = AsyncMock()
    service = AIPromptService(repo)

    # Very long context
    long_spec = EmojiSpecification(context="a" * 500, description="test")
    prompt = await service.build_prompt(long_spec)
    assert len(prompt) <= 1000  # Should truncate/summarize

    # Special characters
    special_spec = EmojiSpecification(
        context="Using <script>alert('test')</script>", description="hacker emoji"
    )
    prompt = await service.build_prompt(special_spec)
    assert "<script>" not in prompt  # Should sanitize


@pytest.mark.asyncio
async def test_generation_service_flow() -> None:
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
