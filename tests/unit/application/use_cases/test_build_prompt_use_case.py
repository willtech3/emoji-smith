"""Tests for BuildPromptUseCase."""

import logging
from unittest.mock import AsyncMock, Mock

import pytest

from emojismith.application.use_cases.build_prompt_use_case import BuildPromptUseCase
from emojismith.domain.repositories.prompt_enhancer_repository import (
    PromptEnhancerRepository,
)
from emojismith.domain.services.description_quality_analyzer import (
    DescriptionQualityAnalyzer,
)
from emojismith.domain.services.prompt_builder_service import PromptBuilderService
from emojismith.domain.value_objects.emoji_specification import EmojiSpecification
from shared.domain.value_objects import EmojiStylePreferences, StyleType


class TestBuildPromptUseCase:
    """Test suite for BuildPromptUseCase."""

    @pytest.fixture()
    def mock_prompt_enhancer(self) -> Mock:
        """Create a mock prompt enhancer repository."""
        repo = Mock(spec=PromptEnhancerRepository)
        repo.enhance_prompt = AsyncMock(return_value="enhanced prompt")
        return repo

    @pytest.fixture()
    def prompt_builder_service(self) -> PromptBuilderService:
        """Create a PromptBuilderService instance."""
        return PromptBuilderService()

    @pytest.fixture()
    def description_quality_analyzer(self) -> DescriptionQualityAnalyzer:
        """Create a real description quality analyzer."""
        return DescriptionQualityAnalyzer(quality_threshold=0.5)

    @pytest.fixture()
    def use_case(
        self,
        mock_prompt_enhancer: Mock,
        prompt_builder_service: PromptBuilderService,
        description_quality_analyzer: DescriptionQualityAnalyzer,
    ) -> BuildPromptUseCase:
        """Create a BuildPromptUseCase instance."""
        return BuildPromptUseCase(
            prompt_enhancer=mock_prompt_enhancer,
            prompt_builder_service=prompt_builder_service,
            description_quality_analyzer=description_quality_analyzer,
        )

    @pytest.fixture()
    def basic_spec(self) -> EmojiSpecification:
        """Create a basic emoji specification."""
        return EmojiSpecification(
            description="celebration",
            context="team just shipped a major feature",
        )

    @pytest.mark.asyncio()
    async def test_build_prompt_without_enhancement(
        self, use_case: BuildPromptUseCase, basic_spec: EmojiSpecification
    ):
        """Should build prompt without AI enhancement when enhance=False."""
        result = await use_case.build_prompt(basic_spec, enhance=False)

        assert "celebration" in result
        assert "emoji" in result.lower() or "icon" in result.lower()
        assert len(result) <= 150

        # Should not call the prompt enhancer
        use_case._prompt_enhancer.enhance_prompt.assert_not_called()

    @pytest.mark.asyncio()
    async def test_build_prompt_with_enhancement(
        self,
        use_case: BuildPromptUseCase,
        basic_spec: EmojiSpecification,
        mock_prompt_enhancer: Mock,
    ):
        """Should enhance prompt using the configured AI provider when enhance=True."""
        # Set up the mock to return a specific enhanced prompt
        mock_prompt_enhancer.enhance_prompt.return_value = (
            "An amazing celebration emoji showing team success and joy"
        )

        result = await use_case.build_prompt(basic_spec, enhance=True)

        assert result == "An amazing celebration emoji showing team success and joy"

        # Should call the prompt enhancer with the built prompt
        mock_prompt_enhancer.enhance_prompt.assert_called_once()
        call_args = mock_prompt_enhancer.enhance_prompt.call_args[0]
        assert "celebration" in call_args[0] or "celebration" in call_args[1]

    @pytest.mark.asyncio()
    async def test_build_prompt_logs_enhancement_event(
        self,
        use_case: BuildPromptUseCase,
        basic_spec: EmojiSpecification,
        mock_prompt_enhancer: Mock,
        caplog,
    ) -> None:
        """Verify prompt enhancement is logged with correct event type."""

        mock_prompt_enhancer.enhance_prompt.return_value = "Enhanced prompt text"

        with caplog.at_level(logging.INFO):
            await use_case.build_prompt(basic_spec, enhance=True)

        enhancement_logs = [
            r
            for r in caplog.records
            if hasattr(r, "event_data")
            and r.event_data.get("event") == "prompt_enhancement"
        ]
        assert len(enhancement_logs) == 1
        assert "original_description" in enhancement_logs[0].event_data
        assert "enhanced_prompt" in enhancement_logs[0].event_data

    @pytest.mark.asyncio()
    async def test_build_prompt_with_style(self, use_case: BuildPromptUseCase):
        """Should include style preferences in the prompt."""
        style_prefs = EmojiStylePreferences(style_type=StyleType.PIXEL_ART)
        spec = EmojiSpecification(
            description="retro game character",
            context="discussing classic arcade games",
            style=style_prefs,
        )

        result = await use_case.build_prompt(spec, enhance=False)

        assert "retro" in result.lower() or "pixel" in result.lower()
        assert "game" in result.lower()
        assert "emoji" in result.lower() or "icon" in result.lower()

    @pytest.mark.asyncio()
    async def test_build_prompt_handles_enhancement_failure(
        self,
        use_case: BuildPromptUseCase,
        basic_spec: EmojiSpecification,
        mock_prompt_enhancer: Mock,
    ):
        """Should fall back to basic prompt if enhancement fails."""
        # Make enhance_prompt raise an exception
        mock_prompt_enhancer.enhance_prompt.side_effect = Exception("AI provider error")

        result = await use_case.build_prompt(basic_spec, enhance=True)

        # Should return the basic prompt instead
        assert "celebration" in result
        assert "emoji" in result.lower() or "icon" in result.lower()
        assert len(result) <= 150

    @pytest.mark.asyncio()
    async def test_build_prompt_preserves_context_themes(
        self, use_case: BuildPromptUseCase
    ):
        """Should extract and include themes from context."""
        spec = EmojiSpecification(
            description="victory dance",
            context=(
                "after working late nights, the team finally "
                "deployed to production successfully"
            ),
        )

        result = await use_case.build_prompt(spec, enhance=False)

        # Should include themes like success, dedication
        assert "success" in result.lower() or "achievement" in result.lower()
        assert "victory" in result.lower()

    @pytest.mark.asyncio()
    async def test_build_prompt_respects_max_length_config(self):
        """Should respect custom max length configuration."""
        prompt_builder = PromptBuilderService(max_prompt_length=80)
        use_case = BuildPromptUseCase(
            prompt_enhancer=Mock(spec=PromptEnhancerRepository),
            prompt_builder_service=prompt_builder,
        )

        spec = EmojiSpecification(
            description=(
                "extremely detailed and complex celebration "
                "with many specific requirements"
            ),
            context=(
                "very long context with lots of details about "
                "the team and project and achievements"
            ),
        )

        result = await use_case.build_prompt(spec, enhance=False)

        assert len(result) <= 80

    @pytest.mark.asyncio()
    async def test_build_prompt_uses_custom_style_when_provided(
        self, use_case: BuildPromptUseCase
    ):
        """Should use custom style parameter when provided."""
        spec = EmojiSpecification(
            description="happy face",
            context="feeling good today",
        )

        result = await use_case.build_prompt(
            spec, enhance=False, style_override="minimalist"
        )

        assert (
            "minimalist" in result.lower()
            or "simple" in result.lower()
            or "clean" in result.lower()
        )

    @pytest.mark.asyncio()
    async def test_build_prompt_enhancement_includes_context_and_description(
        self,
        use_case: BuildPromptUseCase,
        basic_spec: EmojiSpecification,
        mock_prompt_enhancer: Mock,
    ):
        """Should pass both context and description to enhance_prompt."""
        await use_case.build_prompt(basic_spec, enhance=True)

        # Check that enhance_prompt was called with both context and description
        mock_prompt_enhancer.enhance_prompt.assert_called_once()
        call_args = mock_prompt_enhancer.enhance_prompt.call_args[0]

        # The method takes (context, description) as parameters
        assert len(call_args) == 2
        context_arg, description_arg = call_args

        # Verify the arguments contain expected content
        assert (
            "team just shipped" in context_arg or "team just shipped" in description_arg
        )
        assert "celebration" in context_arg or "celebration" in description_arg

    @pytest.mark.asyncio()
    async def test_build_prompt_with_poor_description_uses_fallback(
        self,
        use_case: BuildPromptUseCase,
        mock_prompt_enhancer: Mock,
    ):
        """Test that poor descriptions trigger fallback generation."""
        # Create spec with poor description but good context
        spec = EmojiSpecification(
            description="nice",  # Very vague
            context=(
                "Team successfully deployed the payment processing system to production"
            ),
            style=None,
        )

        # Mock the enhance_prompt to return enhanced version
        mock_prompt_enhancer.enhance_prompt.return_value = "Enhanced emoji prompt"

        # Build prompt
        await use_case.build_prompt(spec, enhance=True)

        # Should have called enhance_prompt with a fallback prompt
        mock_prompt_enhancer.enhance_prompt.assert_called_once()
        _context_arg, prompt_arg = mock_prompt_enhancer.enhance_prompt.call_args[0]

        # The prompt should contain concepts from context, not just "nice"
        assert "nice" not in prompt_arg
        assert any(
            word in prompt_arg.lower()
            for word in ["deployed", "payment", "system", "team"]
        )

    @pytest.mark.asyncio()
    async def test_build_prompt_with_good_description_no_fallback(
        self,
        use_case: BuildPromptUseCase,
        mock_prompt_enhancer: Mock,
    ):
        """Test that good descriptions don't trigger fallback generation."""
        # Create spec with good description
        spec = EmojiSpecification(
            description="happy robot dancing with blue lights",
            context="Celebrating successful automation deployment",
            style=None,
        )

        # Mock the enhance_prompt to return enhanced version
        mock_prompt_enhancer.enhance_prompt.return_value = "Enhanced emoji prompt"

        # Build prompt
        await use_case.build_prompt(spec, enhance=True)

        # Should have called enhance_prompt with the original good description
        mock_prompt_enhancer.enhance_prompt.assert_called_once()
        _context_arg, prompt_arg = mock_prompt_enhancer.enhance_prompt.call_args[0]

        # The prompt should contain the original description
        assert "robot" in prompt_arg.lower()
        assert "dancing" in prompt_arg.lower()

    @pytest.mark.asyncio()
    async def test_build_prompt_logs_fallback_usage(
        self, use_case: BuildPromptUseCase, mock_prompt_enhancer: Mock, caplog
    ):
        """Test that fallback usage is properly logged."""
        # Set log level to capture info messages
        caplog.set_level(logging.INFO)

        # Create spec with poor description
        spec = EmojiSpecification(
            description="emoji", context="Sprint planning meeting", style=None
        )

        # Mock the enhance_prompt to return enhanced version
        mock_prompt_enhancer.enhance_prompt.return_value = "Enhanced emoji prompt"

        # Build prompt
        await use_case.build_prompt(spec, enhance=True)

        # Check logs for fallback notification
        assert any(
            "Using fallback prompt generation" in record.message
            for record in caplog.records
        )
        assert any("score:" in record.message.lower() for record in caplog.records)

    @pytest.mark.asyncio()
    async def test_build_prompt_without_enhancement_still_uses_fallback(
        self, use_case: BuildPromptUseCase, mock_prompt_enhancer: Mock
    ):
        """Test quality analysis and fallback still happens without AI enhancement."""
        # Create spec with poor description
        spec = EmojiSpecification(
            description="nice", context="Team meeting", style=None
        )

        # Build prompt without enhancement
        result = await use_case.build_prompt(spec, enhance=False)

        # Should not have called enhance_prompt
        mock_prompt_enhancer.enhance_prompt.assert_not_called()

        # Result should contain fallback content based on context
        assert "team" in result.lower() or "meeting" in result.lower()
        # The vague word "nice" should not appear in the fallback
        assert "nice" not in result.lower()

    @pytest.mark.asyncio()
    async def test_configurable_quality_threshold(
        self,
        mock_prompt_enhancer: Mock,
        prompt_builder_service: PromptBuilderService,
    ):
        """Test that quality threshold can be configured."""
        # Create analyzer with high threshold
        strict_analyzer = DescriptionQualityAnalyzer(quality_threshold=0.8)

        # Create use case with strict analyzer
        use_case = BuildPromptUseCase(
            prompt_enhancer=mock_prompt_enhancer,
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
        mock_prompt_enhancer.enhance_prompt.return_value = "Enhanced emoji prompt"

        # Build prompt - should trigger fallback due to high threshold
        await use_case.build_prompt(spec, enhance=True)

        # Check that enhance was called with fallback
        _context_arg, prompt_arg = mock_prompt_enhancer.enhance_prompt.call_args[0]

        # Should include context concepts due to strict threshold
        assert any(
            word in prompt_arg.lower() for word in ["completed", "onboarding", "user"]
        )
        # Should not include the vague terms from original description
        assert "good" not in prompt_arg.lower()
