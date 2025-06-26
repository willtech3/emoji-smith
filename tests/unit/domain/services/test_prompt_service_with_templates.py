"""Integration tests for AIPromptService with StyleTemplateManager."""

import pytest
from unittest.mock import AsyncMock, Mock
from emojismith.domain.services.prompt_service import AIPromptService
from emojismith.domain.value_objects.emoji_specification import EmojiSpecification
from shared.domain.value_objects import EmojiStylePreferences, StyleType


class TestAIPromptServiceWithTemplates:
    """Test AIPromptService integration with StyleTemplateManager."""

    @pytest.fixture
    def mock_openai_repo(self):
        """Create mock OpenAI repository."""
        repo = Mock()
        repo.enhance_prompt = AsyncMock()
        return repo

    @pytest.fixture
    def mock_style_template_repository(self):
        """Create mock style template repository."""
        from emojismith.infrastructure.repositories.style_template_config_repository import (  # noqa: E501
            StyleTemplateConfigRepository,
        )

        return StyleTemplateConfigRepository()

    @pytest.fixture
    def style_template_manager(self, mock_style_template_repository):
        """Create StyleTemplateManager instance."""
        from emojismith.domain.services.style_template_manager import (
            StyleTemplateManager,
        )

        return StyleTemplateManager(mock_style_template_repository)

    @pytest.fixture
    def prompt_service(self, mock_openai_repo, style_template_manager):
        """Create AIPromptService instance."""
        return AIPromptService(mock_openai_repo, style_template_manager)

    @pytest.mark.asyncio
    async def test_enhance_uses_style_template_for_cartoon(
        self, prompt_service, mock_openai_repo
    ):
        """Enhance should use style template when style type is specified."""
        spec = EmojiSpecification(
            description="a happy cat",
            context="team celebration",
            style=EmojiStylePreferences(style_type=StyleType.CARTOON),
        )

        result = await prompt_service.enhance(spec)

        # Should use template, not call OpenAI
        assert mock_openai_repo.enhance_prompt.call_count == 0
        assert result.startswith("Create a vibrant, cartoon-style emoji with")
        assert "a happy cat" in result
        assert "Context: team celebration" in result

    @pytest.mark.asyncio
    async def test_enhance_uses_style_template_for_pixel_art(
        self, prompt_service, mock_openai_repo
    ):
        """Enhance should apply pixel art template correctly."""
        spec = EmojiSpecification(
            description="retro game character",
            context="gaming channel",
            style=EmojiStylePreferences(style_type=StyleType.PIXEL_ART),
        )

        result = await prompt_service.enhance(spec)

        assert mock_openai_repo.enhance_prompt.call_count == 0
        assert "Design a retro pixel art emoji showing" in result
        assert "retro game character" in result
        assert "8-bit or 16-bit pixel art style" in result

    @pytest.mark.asyncio
    async def test_enhance_uses_style_template_for_minimalist(
        self, prompt_service, mock_openai_repo
    ):
        """Enhance should apply minimalist template correctly."""
        spec = EmojiSpecification(
            description="thumbs up",
            context="approval",
            style=EmojiStylePreferences(style_type=StyleType.MINIMALIST),
        )

        result = await prompt_service.enhance(spec)

        assert mock_openai_repo.enhance_prompt.call_count == 0
        assert "Create a simple, minimalist emoji depicting" in result
        assert "clean lines, minimal details" in result

    @pytest.mark.asyncio
    async def test_enhance_uses_style_template_for_realistic(
        self, prompt_service, mock_openai_repo
    ):
        """Enhance should apply realistic template correctly."""
        spec = EmojiSpecification(
            description="golden trophy",
            context="achievement unlocked",
            style=EmojiStylePreferences(style_type=StyleType.REALISTIC),
        )

        result = await prompt_service.enhance(spec)

        assert mock_openai_repo.enhance_prompt.call_count == 0
        assert "Generate a realistic, detailed emoji showing" in result
        assert "photorealistic details and natural textures" in result

    @pytest.mark.asyncio
    async def test_enhance_removes_conflicting_words(
        self, prompt_service, mock_openai_repo
    ):
        """Enhance should remove words that conflict with style."""
        spec = EmojiSpecification(
            description="a realistic cartoon character",
            context="fun animation",
            style=EmojiStylePreferences(style_type=StyleType.CARTOON),
        )

        result = await prompt_service.enhance(spec)

        # "realistic" should be removed for cartoon style
        assert "realistic" not in result
        assert "cartoon character" in result

    @pytest.mark.asyncio
    async def test_enhance_falls_back_to_ai_without_style(
        self, prompt_service, mock_openai_repo
    ):
        """Enhance should fall back to AI when no style is specified."""
        spec = EmojiSpecification(
            description="surprise face", context="unexpected news", style=None
        )

        mock_openai_repo.enhance_prompt.return_value = "AI enhanced: surprise face"
        result = await prompt_service.enhance(spec)

        mock_openai_repo.enhance_prompt.assert_called_once_with(
            "unexpected news", "surprise face"
        )
        assert result == "AI enhanced: surprise face"

    @pytest.mark.asyncio
    async def test_enhance_includes_context(self, prompt_service, mock_openai_repo):
        """Enhance should include context when present."""
        spec = EmojiSpecification(
            description="party hat",
            context="celebration",
            style=EmojiStylePreferences(style_type=StyleType.CARTOON),
        )

        result = await prompt_service.enhance(spec)

        assert "Context: celebration" in result
        assert "party hat" in result

    @pytest.mark.asyncio
    async def test_build_prompt_still_works_with_legacy_styles(
        self, prompt_service, mock_openai_repo
    ):
        """Build prompt should still work with legacy style strings."""
        spec = EmojiSpecification(
            description="professional handshake", context="business meeting"
        )

        result = await prompt_service.build_prompt(spec, style="professional")

        assert "professional, business-appropriate emoji" in result
        assert "professional handshake" in result
        assert "Context: business meeting" in result
