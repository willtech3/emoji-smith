"""Tests for AIPromptService."""

from unittest.mock import AsyncMock
from io import BytesIO
from PIL import Image

import pytest

from emojismith.application.services.ai_prompt_service import AIPromptService
from emojismith.domain.value_objects import EmojiSpecification, GeneratedEmoji


class TestAIPromptService:
    """Test AI prompt service pipeline."""

    @staticmethod
    def _sample_spec() -> EmojiSpecification:
        return EmojiSpecification(context="context", description="desc")

    @pytest.fixture
    def mock_ai_repo(self):
        repo = AsyncMock()
        repo.optimize_prompt = AsyncMock(return_value="enhanced")
        img = Image.new("RGBA", (128, 128), (255, 0, 0, 0))
        buf = BytesIO()
        img.save(buf, format="PNG")
        repo.generate_image = AsyncMock(return_value=buf.getvalue())
        return repo

    @pytest.mark.asyncio
    async def test_generate_emoji_calls_openai(self, mock_ai_repo):
        service = AIPromptService(ai_repo=mock_ai_repo)
        spec = self._sample_spec()

        result = await service.generate_emoji(spec)

        mock_ai_repo.optimize_prompt.assert_awaited_once_with(
            context=spec.context,
            description=spec.description,
        )
        mock_ai_repo.generate_image.assert_awaited_once_with(prompt="enhanced")
        assert isinstance(result, GeneratedEmoji)
        assert result.image_data.startswith(b"\x89PNG")
