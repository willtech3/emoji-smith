"""Tests for BuildPromptUseCase."""

from unittest.mock import AsyncMock, Mock

import pytest

from emojismith.application.use_cases.build_prompt_use_case import BuildPromptUseCase
from emojismith.domain.repositories.openai_repository import OpenAIRepository
from emojismith.domain.services.prompt_builder_service import PromptBuilderService
from emojismith.domain.value_objects.emoji_specification import EmojiSpecification
from shared.domain.value_objects import EmojiStylePreferences, StyleType


class TestBuildPromptUseCase:
    """Test suite for BuildPromptUseCase."""

    @pytest.fixture()
    def mock_openai_repo(self) -> Mock:
        """Create a mock OpenAI repository."""
        repo = Mock(spec=OpenAIRepository)
        repo.enhance_prompt = AsyncMock(return_value="enhanced prompt")
        return repo

    @pytest.fixture()
    def prompt_builder_service(self) -> PromptBuilderService:
        """Create a PromptBuilderService instance."""
        return PromptBuilderService()

    @pytest.fixture()
    def use_case(
        self, mock_openai_repo: Mock, prompt_builder_service: PromptBuilderService
    ) -> BuildPromptUseCase:
        """Create a BuildPromptUseCase instance."""
        return BuildPromptUseCase(
            openai_repository=mock_openai_repo,
            prompt_builder_service=prompt_builder_service,
        )

    @pytest.fixture()
    def basic_spec(self) -> EmojiSpecification:
        """Create a basic emoji specification."""
        return EmojiSpecification(
            description="celebration",
            context="team just shipped a major feature",
        )

    async def test_build_prompt_without_enhancement(
        self, use_case: BuildPromptUseCase, basic_spec: EmojiSpecification
    ):
        """Should build prompt without AI enhancement when enhance=False."""
        result = await use_case.build_prompt(basic_spec, enhance=False)

        assert "celebration" in result
        assert "emoji" in result.lower() or "icon" in result.lower()
        assert len(result) <= 150

        # Should not call OpenAI
        use_case._openai_repository.enhance_prompt.assert_not_called()

    async def test_build_prompt_with_enhancement(
        self,
        use_case: BuildPromptUseCase,
        basic_spec: EmojiSpecification,
        mock_openai_repo: Mock,
    ):
        """Should enhance prompt using OpenAI when enhance=True."""
        # Set up the mock to return a specific enhanced prompt
        mock_openai_repo.enhance_prompt.return_value = (
            "An amazing celebration emoji showing team success and joy"
        )

        result = await use_case.build_prompt(basic_spec, enhance=True)

        assert result == "An amazing celebration emoji showing team success and joy"

        # Should call OpenAI with the built prompt
        mock_openai_repo.enhance_prompt.assert_called_once()
        call_args = mock_openai_repo.enhance_prompt.call_args[0]
        assert "celebration" in call_args[0] or "celebration" in call_args[1]

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

    async def test_build_prompt_handles_enhancement_failure(
        self,
        use_case: BuildPromptUseCase,
        basic_spec: EmojiSpecification,
        mock_openai_repo: Mock,
    ):
        """Should fall back to basic prompt if enhancement fails."""
        # Make enhance_prompt raise an exception
        mock_openai_repo.enhance_prompt.side_effect = Exception("OpenAI API error")

        result = await use_case.build_prompt(basic_spec, enhance=True)

        # Should return the basic prompt instead
        assert "celebration" in result
        assert "emoji" in result.lower() or "icon" in result.lower()
        assert len(result) <= 150

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

    async def test_build_prompt_respects_max_length_config(self):
        """Should respect custom max length configuration."""
        prompt_builder = PromptBuilderService(max_prompt_length=80)
        use_case = BuildPromptUseCase(
            openai_repository=Mock(spec=OpenAIRepository),
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

    async def test_build_prompt_enhancement_includes_context_and_description(
        self,
        use_case: BuildPromptUseCase,
        basic_spec: EmojiSpecification,
        mock_openai_repo: Mock,
    ):
        """Should pass both context and description to enhance_prompt."""
        await use_case.build_prompt(basic_spec, enhance=True)

        # Check that enhance_prompt was called with both context and description
        mock_openai_repo.enhance_prompt.assert_called_once()
        call_args = mock_openai_repo.enhance_prompt.call_args[0]

        # The method takes (context, description) as parameters
        assert len(call_args) == 2
        context_arg, description_arg = call_args

        # Verify the arguments contain expected content
        assert (
            "team just shipped" in context_arg or "team just shipped" in description_arg
        )
        assert "celebration" in context_arg or "celebration" in description_arg
