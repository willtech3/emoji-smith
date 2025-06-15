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


@pytest.mark.asyncio
async def test_respects_environment_model_configuration() -> None:
    """Test that repository respects OPENAI_CHAT_MODEL from environment."""
    import os

    # Set environment variable
    os.environ["OPENAI_CHAT_MODEL"] = "gpt-4-turbo"

    client = AsyncMock()
    client.models.retrieve = AsyncMock(return_value=None)
    client.chat.completions.create.return_value = AsyncMock(
        choices=[AsyncMock(message=AsyncMock(content="response"))]
    )

    # Create repository with environment model
    repo = OpenAIAPIRepository(client, model=os.getenv("OPENAI_CHAT_MODEL", "o3"))
    result = await repo.enhance_prompt("context", "description")

    # Verify it uses the environment-configured model
    assert result == "response"
    assert client.chat.completions.create.call_args.kwargs["model"] == "gpt-4-turbo"

    # Clean up
    del os.environ["OPENAI_CHAT_MODEL"]


@pytest.mark.asyncio
async def test_generate_image_raises_on_missing_data() -> None:
    client = AsyncMock()
    client.images.generate.return_value = AsyncMock(data=[])
    repo = OpenAIAPIRepository(client)
    with pytest.raises(ValueError):
        await repo.generate_image("p")
