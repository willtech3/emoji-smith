"""Tests for OpenAIAPIRepository."""

import pytest
from unittest.mock import AsyncMock
from emojismith.infrastructure.openai.openai_api import OpenAIAPIRepository


@pytest.mark.asyncio
async def test_enhance_prompt_calls_client() -> None:
    client = AsyncMock()
    client.chat.completions.create.return_value = AsyncMock(
        choices=[AsyncMock(message=AsyncMock(content="ok"))]
    )
    repo = OpenAIAPIRepository(client)
    result = await repo.enhance_prompt("ctx", "desc")
    assert result == "ok"
    client.chat.completions.create.assert_called_once()


@pytest.mark.asyncio
async def test_enhance_prompt_falls_back_on_missing_model() -> None:
    client = AsyncMock()
    client.models.retrieve = AsyncMock(side_effect=[Exception(), None])
    client.chat.completions.create.return_value = AsyncMock(
        choices=[AsyncMock(message=AsyncMock(content="fine"))]
    )
    repo = OpenAIAPIRepository(client, model="o3", fallback_models=["gpt-4"])
    result = await repo.enhance_prompt("ctx", "desc")
    assert result == "fine"
    client.chat.completions.create.assert_called_once()
    assert client.chat.completions.create.call_args.kwargs["model"] == "gpt-4"


@pytest.mark.asyncio
async def test_generate_image_calls_client() -> None:
    client = AsyncMock()
    client.images.generate.return_value = AsyncMock(
        data=[AsyncMock(b64_json="aGVsbG8=")]
    )
    repo = OpenAIAPIRepository(client)
    data = await repo.generate_image("prompt")
    assert isinstance(data, bytes)
    client.images.generate.assert_called_once_with(
        model="dall-e-3", prompt="prompt", n=1, size="1024x1024"
    )


@pytest.mark.asyncio
async def test_generate_image_raises_on_missing_data() -> None:
    client = AsyncMock()
    client.images.generate.return_value = AsyncMock(data=[])
    repo = OpenAIAPIRepository(client)
    with pytest.raises(ValueError):
        await repo.generate_image("p")
