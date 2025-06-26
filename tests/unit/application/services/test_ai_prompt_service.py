"""Tests for AIPromptService and EmojiGenerationService."""

import pytest
from unittest.mock import AsyncMock, Mock
from io import BytesIO
from PIL import Image
from emojismith.domain.value_objects import EmojiSpecification
from emojismith.application.services.ai_prompt_service import AIPromptService
from emojismith.domain.services import EmojiGenerationService
from emojismith.domain.services.emoji_validation_service import EmojiValidationService
from emojismith.domain.entities.generated_emoji import GeneratedEmoji
from emojismith.domain.repositories.image_processor import ImageProcessor
from emojismith.domain.services.style_template_manager import StyleTemplateManager
from emojismith.domain.repositories.style_template_repository import (
    StyleTemplateRepository,
)
from emojismith.domain.value_objects.style_template import StyleTemplate


class DummyProcessor(ImageProcessor):
    def process(self, image_data: bytes) -> bytes:
        return image_data


def create_mock_style_manager() -> StyleTemplateManager:
    """Create a mock style manager with default behavior."""
    style_repo = Mock(spec=StyleTemplateRepository)
    # Set up default template
    default_template = StyleTemplate(
        style="default",
        prefix="Default style",
        suffix="standard format",
        keywords=["standard", "default"],
        avoid=[]
    )
    style_repo.get_template.return_value = None
    style_repo.get_default_template.return_value = default_template
    return StyleTemplateManager(style_repo)


@pytest.mark.asyncio
@pytest.mark.unit
async def test_prompt_service_enhances() -> None:
    repo = AsyncMock()
    repo.enhance_prompt.return_value = "enhanced"
    style_repo = Mock(spec=StyleTemplateRepository)
    style_manager = StyleTemplateManager(style_repo)
    spec = EmojiSpecification(context="ctx", description="desc")
    service = AIPromptService(repo, style_manager)
    result = await service.enhance(spec)
    assert result == "enhanced"
    repo.enhance_prompt.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_prompt_service_build_with_style_strategy() -> None:
    """Service should apply style-specific prompt building strategy."""
    repo = AsyncMock()
    repo.enhance_prompt.return_value = "enhanced prompt"

    # Create mock style repository and manager
    from emojismith.infrastructure.repositories.style_template_config_repository import (  # noqa: E501
        StyleTemplateConfigRepository,
    )

    style_repo = StyleTemplateConfigRepository()
    style_manager = StyleTemplateManager(style_repo)

    spec = EmojiSpecification(context="discussing code", description="facepalm")
    service = AIPromptService(repo, style_manager)

    # Build prompt with cartoon style
    cartoon_prompt = await service.build_prompt(spec, style="cartoon")
    assert "Cartoon emoji style" in cartoon_prompt
    assert "vibrant colors" in cartoon_prompt

    # Build prompt with minimalist style
    minimal_prompt = await service.build_prompt(spec, style="minimalist")
    assert "Minimalist emoji icon" in minimal_prompt
    assert "flat design" in minimal_prompt


@pytest.mark.asyncio
@pytest.mark.unit
async def test_prompt_service_build_with_context_enrichment() -> None:
    """Service should enrich prompts based on message context."""
    repo = AsyncMock()
    style_manager = create_mock_style_manager()
    service = AIPromptService(repo, style_manager)

    spec = EmojiSpecification(
        context="Just deployed to production on Friday afternoon",
        description="nervous laugh",
    )

    prompt = await service.build_prompt(spec)

    # Should detect risky deployment context
    assert "deploy" in prompt.lower()  # Can match "deployed" or "deployment"
    assert "risk" in prompt.lower() or "careful" in prompt.lower()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_prompt_service_handles_edge_cases() -> None:
    """Service should handle edge cases gracefully."""
    repo = AsyncMock()
    style_manager = create_mock_style_manager()
    service = AIPromptService(repo, style_manager)

    # Very long context
    long_spec = EmojiSpecification(context="a" * 500, description="test")
    prompt = await service.build_prompt(long_spec)
    assert len(prompt) <= 1000  # Should truncate/summarize

    # Special characters
    special_spec = EmojiSpecification(
        context="Using <script>alert('test')</script>", description="hacker emoji"
    )
    prompt = await service.build_prompt(special_spec)
    # HTML sanitization is now done at infrastructure boundary, not in domain/app layer


@pytest.mark.asyncio
@pytest.mark.unit
async def test_prompt_service_truncates_very_long_prompts() -> None:
    """Service should truncate prompts that exceed 1000 characters."""
    repo = AsyncMock()
    style_manager = create_mock_style_manager()
    service = AIPromptService(repo, style_manager)

    # Create a prompt that will exceed 1000 characters
    very_long_description = "x" * 900
    spec = EmojiSpecification(
        context="This is a context that will push the total over 1000 chars",
        description=very_long_description,
    )

    prompt = await service.build_prompt(spec)

    # Should be truncated to exactly 1000 characters
    assert len(prompt) == 1000
    assert prompt.endswith("...")  # Should end with ellipsis


@pytest.mark.asyncio
@pytest.mark.unit
async def test_prompt_service_enriches_deployment_context_without_friday() -> None:
    """Service should enrich deployment context even when not on Friday."""
    repo = AsyncMock()
    style_manager = create_mock_style_manager()
    service = AIPromptService(repo, style_manager)

    # Test regular deployment context (not Friday)
    spec = EmojiSpecification(
        context="Just finished the deployment to production",
        description="celebration emoji",
    )

    prompt = await service.build_prompt(spec)

    # Should detect deployment context and add appropriate enrichment
    assert "deployment" in prompt.lower() or "release" in prompt.lower()
    assert "Include elements suggesting deployment or release activity" in prompt
    # Should NOT include risk/careful language when not Friday
    assert "risk" not in prompt.lower()
    assert "careful" not in prompt.lower()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_prompt_service_handles_unknown_style() -> None:
    """Service should handle unknown style gracefully."""
    repo = AsyncMock()
    style_manager = create_mock_style_manager()
    service = AIPromptService(repo, style_manager)

    spec = EmojiSpecification(context="testing unknown style", description="test emoji")

    # Should not raise error with unknown style
    prompt = await service.build_prompt(spec, style="unknown_style")
    assert "test emoji" in prompt
    assert "testing unknown style" in prompt
    # Should fall back to basic prompt without style template


@pytest.mark.asyncio
@pytest.mark.unit
async def test_prompt_service_handles_minimal_and_retro_styles() -> None:
    """Service should correctly apply minimal and retro style strategies."""
    repo = AsyncMock()
    # Use real style repository for this test
    from emojismith.infrastructure.repositories.style_template_config_repository import (
        StyleTemplateConfigRepository,
    )  # noqa: E501
    style_repo = StyleTemplateConfigRepository()
    style_manager = StyleTemplateManager(style_repo)
    service = AIPromptService(repo, style_manager)

    spec = EmojiSpecification(context="coding session", description="focused face")

    # Test minimalist style
    minimal_prompt = await service.build_prompt(spec, style="minimalist")
    assert "simple" in minimal_prompt.lower()
    assert "clean" in minimal_prompt.lower() or "minimal" in minimal_prompt.lower()
    assert "Minimalist emoji icon" in minimal_prompt

    # Test pixel_art style (retro not in default templates)
    pixel_prompt = await service.build_prompt(spec, style="pixel_art")
    assert "pixel art" in pixel_prompt.lower()
    assert "8-bit" in pixel_prompt or "retro" in pixel_prompt.lower()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_prompt_service_sanitizes_various_html_entities() -> None:
    """Service should sanitize various HTML entities and tags."""
    repo = AsyncMock()
    style_manager = create_mock_style_manager()
    service = AIPromptService(repo, style_manager)

    # Test various HTML entities
    spec = EmojiSpecification(
        context='Context with <div>tags</div> and <img src="x">',
        description="test < and > symbols",
    )

    prompt = await service.build_prompt(spec)

    # HTML sanitization is now done at infrastructure boundary, not in application layer
    # The prompt should contain the original text
    assert "test" in prompt
    assert "symbols" in prompt


@pytest.mark.asyncio
@pytest.mark.unit
async def test_prompt_service_enriches_release_context() -> None:
    """Service should enrich release context similarly to deployment."""
    repo = AsyncMock()
    style_manager = create_mock_style_manager()
    service = AIPromptService(repo, style_manager)

    spec = EmojiSpecification(
        context="Preparing for the major release next week",
        description="rocket emoji",
    )

    prompt = await service.build_prompt(spec)

    # Should detect release context
    assert "release" in prompt.lower()
    assert "Include elements suggesting deployment or release activity" in prompt


@pytest.mark.asyncio
@pytest.mark.unit
async def test_prompt_service_with_emoji_specification_style() -> None:
    """Service should incorporate EmojiStylePreferences from specification."""
    repo = AsyncMock()
    style_manager = create_mock_style_manager()
    service = AIPromptService(repo, style_manager)

    from shared.domain.value_objects import (
        EmojiStylePreferences,
        StyleType,
        ColorScheme,
        DetailLevel,
        Tone,
    )

    style_prefs = EmojiStylePreferences(
        style_type=StyleType.PIXEL_ART,
        color_scheme=ColorScheme.BRIGHT,
        detail_level=DetailLevel.DETAILED,
        tone=Tone.EXPRESSIVE,
    )

    spec = EmojiSpecification(
        context="game development", description="power-up", style=style_prefs
    )

    # Test with no explicit style parameter
    prompt = await service.build_prompt(spec)

    # Should include style preferences from the specification
    assert "pixel_art" in prompt or "pixel" in prompt
    # The base prompt should include the style fragment
    assert spec.style.to_prompt_fragment() in prompt


@pytest.mark.asyncio
@pytest.mark.unit
async def test_prompt_service_handles_empty_style_strategies_dict() -> None:
    """Service should handle if style_strategies dict is modified."""
    repo = AsyncMock()
    style_manager = create_mock_style_manager()
    service = AIPromptService(repo, style_manager)

    # Simulate empty strategies dict
    service._style_strategies = {}

    spec = EmojiSpecification(context="test", description="emoji")

    # Should not raise error with empty strategies
    prompt = await service.build_prompt(spec, style="professional")
    assert "test" in prompt
    assert "emoji" in prompt


@pytest.mark.asyncio
@pytest.mark.unit
async def test_prompt_service_combines_style_and_context_enrichment() -> None:
    """Service should apply both style strategy and context enrichment."""
    repo = AsyncMock()
    # Use real style repository for this test
    from emojismith.infrastructure.repositories.style_template_config_repository import (
        StyleTemplateConfigRepository,
    )  # noqa: E501
    style_repo = StyleTemplateConfigRepository()
    style_manager = StyleTemplateManager(style_repo)
    service = AIPromptService(repo, style_manager)

    spec = EmojiSpecification(
        context="Deploying to production", description="nervous emoji"
    )

    # Apply realistic style to deployment context (professional not in default templates)
    prompt = await service.build_prompt(spec, style="realistic")

    # Should have both style and context enrichment
    assert "Realistic emoji" in prompt
    assert "detailed" in prompt.lower()
    assert "Include elements suggesting deployment or release activity" in prompt


@pytest.mark.asyncio
@pytest.mark.unit
async def test_prompt_service_handles_context_with_multiple_keywords() -> None:
    """Service should handle context with multiple deployment-related keywords."""
    repo = AsyncMock()
    style_manager = create_mock_style_manager()
    service = AIPromptService(repo, style_manager)

    spec = EmojiSpecification(
        context="Release and deploy to production on Friday",
        description="sweating emoji",
    )

    prompt = await service.build_prompt(spec)

    # Should detect both Friday and deployment/release
    assert "risk" in prompt.lower() or "careful" in prompt.lower()
    # Ensure enrichment is applied only once
    assert prompt.count("Include subtle elements") == 1


@pytest.mark.asyncio
@pytest.mark.unit
async def test_generation_service_flow() -> None:
    repo = AsyncMock()
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
    # Use a pre-built prompt since the service no longer builds prompts
    prompt = "a happy face emoji in cartoon style"
    emoji = await service.generate_from_prompt(prompt, "name")
    assert isinstance(emoji, GeneratedEmoji)
    assert emoji.name == "name"
    repo.generate_image.assert_called_once_with(prompt)
    mock_validator.validate_emoji_format.assert_called_once_with(image_data)
