"""Tests for OpenAI API infrastructure implementation."""

from unittest.mock import AsyncMock

import pytest

from emojismith.infrastructure.openai.openai_api import OpenAIAPIRepository


class FakeOpenAIClient:
    def __init__(self) -> None:
        self.chat = AsyncMock()
        self.chat.completions = AsyncMock()
        self.chat.completions.create = AsyncMock()
        self.images = AsyncMock()
        self.images.generate = AsyncMock()


class TestOpenAIAPIRepository:
    """Test OpenAI API repository implementation."""

    @pytest.fixture
    def mock_openai_client(self) -> FakeOpenAIClient:
        return FakeOpenAIClient()

    @pytest.fixture
    def openai_repo(self, mock_openai_client: FakeOpenAIClient) -> OpenAIAPIRepository:
        return OpenAIAPIRepository(client=mock_openai_client)

    @pytest.mark.asyncio
    async def test_optimize_prompt_calls_openai(self, openai_repo, mock_openai_client):
        mock_openai_client.chat.completions.create.return_value = AsyncMock(
            choices=[AsyncMock(message=AsyncMock(content="opt"))]
        )

        result = await openai_repo.optimize_prompt("ctx", "desc")

        mock_openai_client.chat.completions.create.assert_awaited_once()
        assert result == "opt"

    @pytest.mark.asyncio
    async def test_generate_image_calls_openai(self, openai_repo, mock_openai_client):
        mock_openai_client.images.generate.return_value = AsyncMock(
            data=[AsyncMock(b64_json="aGVsbG8=")]
        )

        result = await openai_repo.generate_image("prompt")

        mock_openai_client.images.generate.assert_awaited_once()
        assert result == b"hello"
