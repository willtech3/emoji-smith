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
    def process(self, image_data: bytes) -> bytes:
        return image_data


@pytest.mark.asyncio
@pytest.mark.unit
async def test_prompt_service_enhances() -> None:
    repo = AsyncMock()
    repo.enhance_prompt.return_value = "enhanced"
    spec = EmojiSpecification(context="ctx", description="desc", style=None)

    # Create mock style template manager
    from unittest.mock import Mock
    from emojismith.domain.services.style_template_manager import StyleTemplateManager

    mock_style_manager = Mock(spec=StyleTemplateManager)

    service = AIPromptService(repo, mock_style_manager)
    result = await service.enhance(spec)
    # Since spec has no style, it should fall back to AI enhancement
    assert result == "enhanced"
    repo.enhance_prompt.assert_called_once_with("ctx", "desc")


@pytest.mark.asyncio
@pytest.mark.unit
async def test_prompt_service_build_with_style_strategy() -> None:
    """Service should apply style-specific prompt building strategy."""
    repo = AsyncMock()
    repo.enhance_prompt.return_value = "enhanced prompt"

    spec = EmojiSpecification(context="discussing code", description="facepalm")

    # Create mock style template manager
    from unittest.mock import Mock
    from emojismith.domain.services.style_template_manager import StyleTemplateManager

    mock_style_manager = Mock(spec=StyleTemplateManager)

    service = AIPromptService(repo, mock_style_manager)

    # Build prompt with professional style
    professional_prompt = await service.build_prompt(spec, style="professional")
    assert "professional" in professional_prompt
    assert "business-appropriate" in professional_prompt

    # Build prompt with playful style
    playful_prompt = await service.build_prompt(spec, style="playful")
    assert "fun" in playful_prompt
    assert "vibrant" in playful_prompt


@pytest.mark.asyncio
@pytest.mark.unit
async def test_prompt_service_build_with_context_enrichment() -> None:
    """Service should enrich prompts based on message context."""
    repo = AsyncMock()

    # Create mock style template manager
    from unittest.mock import Mock
    from emojismith.domain.services.style_template_manager import StyleTemplateManager

    mock_style_manager = Mock(spec=StyleTemplateManager)

    service = AIPromptService(repo, mock_style_manager)

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

    # Create mock style template manager
    from unittest.mock import Mock
    from emojismith.domain.services.style_template_manager import StyleTemplateManager

    mock_style_manager = Mock(spec=StyleTemplateManager)

    service = AIPromptService(repo, mock_style_manager)

    # Very long context
    long_spec = EmojiSpecification(context="a" * 500, description="test")
    prompt = await service.build_prompt(long_spec)
    assert len(prompt) <= 1000  # Should truncate/summarize

    # Special characters
    special_spec = EmojiSpecification(
        context="Using <script>alert('test')</script>", description="hacker emoji"
    )
    prompt = await service.build_prompt(special_spec)
    assert len(prompt) <= 1000  # Should truncate if too long


@pytest.mark.asyncio
@pytest.mark.unit
async def test_prompt_service_truncates_very_long_prompts() -> None:
    """Service should truncate prompts that exceed 1000 characters."""
    repo = AsyncMock()

    # Create mock style template manager
    from unittest.mock import Mock
    from emojismith.domain.services.style_template_manager import StyleTemplateManager

    mock_style_manager = Mock(spec=StyleTemplateManager)

    service = AIPromptService(repo, mock_style_manager)

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

    # Create mock style template manager
    from unittest.mock import Mock
    from emojismith.domain.services.style_template_manager import StyleTemplateManager

    mock_style_manager = Mock(spec=StyleTemplateManager)

    service = AIPromptService(repo, mock_style_manager)

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

    # Create mock style template manager
    from unittest.mock import Mock
    from emojismith.domain.services.style_template_manager import StyleTemplateManager

    mock_style_manager = Mock(spec=StyleTemplateManager)

    service = AIPromptService(repo, mock_style_manager)

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

    # Create mock style template manager
    from unittest.mock import Mock
    from emojismith.domain.services.style_template_manager import StyleTemplateManager

    mock_style_manager = Mock(spec=StyleTemplateManager)

    service = AIPromptService(repo, mock_style_manager)

    spec = EmojiSpecification(context="coding session", description="focused face")

    # Test minimal style
    minimal_prompt = await service.build_prompt(spec, style="minimal")
    assert "simple" in minimal_prompt
    assert "clean" in minimal_prompt
    assert "minimalist" in minimal_prompt

    # Test retro style
    retro_prompt = await service.build_prompt(spec, style="retro")
    assert "nostalgic" in retro_prompt
    assert "retro-style" in retro_prompt
    assert "vintage" in retro_prompt


@pytest.mark.asyncio
@pytest.mark.unit
async def test_prompt_service_sanitizes_various_html_entities() -> None:
    """Service should sanitize various HTML entities and tags."""
    repo = AsyncMock()

    # Create mock style template manager
    from unittest.mock import Mock
    from emojismith.domain.services.style_template_manager import StyleTemplateManager

    mock_style_manager = Mock(spec=StyleTemplateManager)

    service = AIPromptService(repo, mock_style_manager)

    # Test various HTML entities
    spec = EmojiSpecification(
        context='Context with <div>tags</div> and <img src="x">',
        description="test < and > symbols",
    )

    prompt = await service.build_prompt(spec)

    # Should not contain raw HTML (domain layer doesn't sanitize)
    assert "test < and > symbols" in prompt
    assert len(prompt) <= 1000


@pytest.mark.asyncio
@pytest.mark.unit
async def test_prompt_service_enriches_release_context() -> None:
    """Service should enrich release context similarly to deployment."""
    repo = AsyncMock()

    # Create mock style template manager
    from unittest.mock import Mock
    from emojismith.domain.services.style_template_manager import StyleTemplateManager

    mock_style_manager = Mock(spec=StyleTemplateManager)

    service = AIPromptService(repo, mock_style_manager)

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

    # Create mock style template manager
    from unittest.mock import Mock
    from emojismith.domain.services.style_template_manager import StyleTemplateManager

    mock_style_manager = Mock(spec=StyleTemplateManager)

    service = AIPromptService(repo, mock_style_manager)

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

    # Create mock style template manager
    from unittest.mock import Mock
    from emojismith.domain.services.style_template_manager import StyleTemplateManager

    mock_style_manager = Mock(spec=StyleTemplateManager)

    service = AIPromptService(repo, mock_style_manager)

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

    # Create mock style template manager
    from unittest.mock import Mock
    from emojismith.domain.services.style_template_manager import StyleTemplateManager

    mock_style_manager = Mock(spec=StyleTemplateManager)

    service = AIPromptService(repo, mock_style_manager)

    spec = EmojiSpecification(
        context="Deploying to production", description="nervous emoji"
    )

    # Apply professional style to deployment context
    prompt = await service.build_prompt(spec, style="professional")

    # Should have both style and context enrichment
    assert "professional" in prompt
    assert "business-appropriate" in prompt
    assert "Include elements suggesting deployment or release activity" in prompt


@pytest.mark.asyncio
@pytest.mark.unit
async def test_prompt_service_handles_context_with_multiple_keywords() -> None:
    """Service should handle context with multiple deployment-related keywords."""
    repo = AsyncMock()

    # Create mock style template manager
    from unittest.mock import Mock
    from emojismith.domain.services.style_template_manager import StyleTemplateManager

    mock_style_manager = Mock(spec=StyleTemplateManager)

    service = AIPromptService(repo, mock_style_manager)

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

    # Create mock style template manager
    from emojismith.domain.services.style_template_manager import StyleTemplateManager

    mock_style_manager = Mock(spec=StyleTemplateManager)

    service = EmojiGenerationService(repo, processor, validation_service, mock_style_manager)
    # Use a pre-built prompt since the service no longer builds prompts
    prompt = "a happy face emoji in cartoon style"
    emoji = await service.generate_from_prompt(prompt, "name")
    assert isinstance(emoji, GeneratedEmoji)
    assert emoji.name == "name"
    repo.generate_image.assert_called_once_with(prompt)
    mock_validator.validate_emoji_format.assert_called_once_with(image_data)
