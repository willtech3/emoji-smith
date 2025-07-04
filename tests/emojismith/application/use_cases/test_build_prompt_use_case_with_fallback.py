"""Tests for BuildPromptUseCase with description quality analyzer integration."""

import pytest
from unittest.mock import Mock, AsyncMock
from emojismith.application.use_cases.build_prompt_use_case import BuildPromptUseCase
from emojismith.domain.services.prompt_builder_service import PromptBuilderService
from emojismith.domain.services.description_quality_analyzer import (
    DescriptionQualityAnalyzer,
)
from emojismith.domain.value_objects.emoji_specification import EmojiSpecification


@pytest.fixture
def mock_openai_repository():
    """Create a mock OpenAI repository."""
    repo = Mock()
    repo.enhance_prompt = AsyncMock()
    return repo


@pytest.fixture
def prompt_builder_service():
    """Create a real prompt builder service."""
    return PromptBuilderService()


@pytest.fixture
def description_quality_analyzer():
    """Create a real description quality analyzer."""
    return DescriptionQualityAnalyzer(quality_threshold=0.5)


@pytest.mark.asyncio
async def test_build_prompt_with_poor_description_uses_fallback(
    mock_openai_repository, prompt_builder_service, description_quality_analyzer
):
    """Test that poor descriptions trigger fallback generation."""
    # Create use case with analyzer
    use_case = BuildPromptUseCase(
        openai_repository=mock_openai_repository,
        prompt_builder_service=prompt_builder_service,
        description_quality_analyzer=description_quality_analyzer,
    )

    # Create spec with poor description but good context
    spec = EmojiSpecification(
        description="nice",  # Very vague
        context="Team successfully deployed the payment processing system to "
        "production",
        style=None,
    )

    # Mock the enhance_prompt to return enhanced version
    mock_openai_repository.enhance_prompt.return_value = "Enhanced emoji prompt"

    # Build prompt
    await use_case.build_prompt(spec, enhance=True)

    # Should have called enhance_prompt with a fallback prompt
    mock_openai_repository.enhance_prompt.assert_called_once()
    context_arg, prompt_arg = mock_openai_repository.enhance_prompt.call_args[0]

    # The prompt should contain concepts from context, not just "nice"
    assert "nice" not in prompt_arg
    assert any(
        word in prompt_arg.lower() for word in ["deployed", "payment", "system", "team"]
    )


@pytest.mark.asyncio
async def test_build_prompt_with_good_description_no_fallback(
    mock_openai_repository, prompt_builder_service, description_quality_analyzer
):
    """Test that good descriptions don't trigger fallback generation."""
    # Create use case with analyzer
    use_case = BuildPromptUseCase(
        openai_repository=mock_openai_repository,
        prompt_builder_service=prompt_builder_service,
        description_quality_analyzer=description_quality_analyzer,
    )

    # Create spec with good description
    spec = EmojiSpecification(
        description="happy robot dancing with blue lights",
        context="Celebrating successful automation deployment",
        style=None,
    )

    # Mock the enhance_prompt to return enhanced version
    mock_openai_repository.enhance_prompt.return_value = "Enhanced emoji prompt"

    # Build prompt
    await use_case.build_prompt(spec, enhance=True)

    # Should have called enhance_prompt with the original good description
    mock_openai_repository.enhance_prompt.assert_called_once()
    context_arg, prompt_arg = mock_openai_repository.enhance_prompt.call_args[0]

    # The prompt should contain the original description
    assert "robot" in prompt_arg.lower()
    assert "dancing" in prompt_arg.lower()


@pytest.mark.asyncio
async def test_build_prompt_logs_fallback_usage(
    mock_openai_repository, prompt_builder_service, description_quality_analyzer, caplog
):
    """Test that fallback usage is properly logged."""
    import logging

    # Set log level to capture info messages
    caplog.set_level(logging.INFO)

    # Create use case with analyzer
    use_case = BuildPromptUseCase(
        openai_repository=mock_openai_repository,
        prompt_builder_service=prompt_builder_service,
        description_quality_analyzer=description_quality_analyzer,
    )

    # Create spec with poor description
    spec = EmojiSpecification(
        description="emoji", context="Sprint planning meeting", style=None
    )

    # Mock the enhance_prompt to return enhanced version
    mock_openai_repository.enhance_prompt.return_value = "Enhanced emoji prompt"

    # Build prompt
    await use_case.build_prompt(spec, enhance=True)

    # Check logs for fallback notification
    assert any(
        "Using fallback prompt generation" in record.message
        for record in caplog.records
    )
    assert any("score:" in record.message.lower() for record in caplog.records)


@pytest.mark.asyncio
async def test_build_prompt_without_enhancement_still_uses_fallback(
    mock_openai_repository, prompt_builder_service, description_quality_analyzer
):
    """Test that quality analysis and fallback still happens even without
    AI enhancement."""
    # Create use case with analyzer
    use_case = BuildPromptUseCase(
        openai_repository=mock_openai_repository,
        prompt_builder_service=prompt_builder_service,
        description_quality_analyzer=description_quality_analyzer,
    )

    # Create spec with poor description
    spec = EmojiSpecification(description="nice", context="Team meeting", style=None)

    # Build prompt without enhancement
    result = await use_case.build_prompt(spec, enhance=False)

    # Should not have called enhance_prompt
    mock_openai_repository.enhance_prompt.assert_not_called()

    # Result should contain fallback content based on context
    assert "team" in result.lower() or "meeting" in result.lower()
    # The vague word "nice" should not appear in the fallback
    assert "nice" not in result.lower()


@pytest.mark.asyncio
async def test_configurable_quality_threshold(
    mock_openai_repository, prompt_builder_service
):
    """Test that quality threshold can be configured."""
    # Create analyzer with high threshold
    strict_analyzer = DescriptionQualityAnalyzer(quality_threshold=0.8)

    # Create use case with strict analyzer
    use_case = BuildPromptUseCase(
        openai_repository=mock_openai_repository,
        prompt_builder_service=prompt_builder_service,
        description_quality_analyzer=strict_analyzer,
    )

    # Create spec with medium quality description
    spec = EmojiSpecification(
        description="good icon",  # Medium quality - will be below 0.8 threshold
        context="User completed onboarding",
        style=None,
    )

    # Mock the enhance_prompt
    mock_openai_repository.enhance_prompt.return_value = "Enhanced emoji prompt"

    # Build prompt - should trigger fallback due to high threshold
    await use_case.build_prompt(spec, enhance=True)

    # Check that enhance was called with fallback
    context_arg, prompt_arg = mock_openai_repository.enhance_prompt.call_args[0]

    # Should include context concepts due to strict threshold
    assert any(
        word in prompt_arg.lower() for word in ["completed", "onboarding", "user"]
    )
    # Should not include the vague terms from original description
    assert "good" not in prompt_arg.lower()
