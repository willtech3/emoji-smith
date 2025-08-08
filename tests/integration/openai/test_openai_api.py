"""Tests for OpenAIAPIRepository."""

from unittest.mock import AsyncMock

import httpx
import openai
import pytest

from emojismith.domain.errors import RateLimitExceededError
from emojismith.infrastructure.openai.openai_api import OpenAIAPIRepository


@pytest.mark.asyncio()
@pytest.mark.integration()
async def test_enhances_prompt_with_ai_assistance() -> None:
    client = AsyncMock()
    client.chat.completions.create.return_value = AsyncMock(
        choices=[AsyncMock(message=AsyncMock(content="ok"))]
    )
    repo = OpenAIAPIRepository(client)
    result = await repo.enhance_prompt("ctx", "desc")
    assert result == "ok"
    client.chat.completions.create.assert_called_once()


@pytest.mark.asyncio()
@pytest.mark.integration()
async def test_enhance_prompt_uses_comprehensive_system_prompt() -> None:
    """Test that enhance_prompt uses a comprehensive system prompt for gpt-image."""
    client = AsyncMock()
    client.chat.completions.create.return_value = AsyncMock(
        choices=[AsyncMock(message=AsyncMock(content="enhanced prompt"))]
    )
    repo = OpenAIAPIRepository(client)

    context = "Team celebration"
    description = "party popper emoji"

    result = await repo.enhance_prompt(context, description)

    # Verify the API was called
    assert result == "enhanced prompt"
    client.chat.completions.create.assert_called_once()

    # Extract the system prompt used
    call_args = client.chat.completions.create.call_args
    messages = call_args.kwargs["messages"]
    system_prompt = messages[0]["content"]

    # Verify the system prompt contains key requirements for gpt-image emoji generation
    assert "transparent background" in system_prompt.lower()
    assert "128x128" in system_prompt
    assert "slack" in system_prompt.lower()
    assert "emoji" in system_prompt.lower()
    assert "gpt-image" in system_prompt.lower()
    assert (
        len(system_prompt) > 100
    )  # Should be comprehensive, not just "Enhance emoji prompt"


@pytest.mark.asyncio()
@pytest.mark.integration()
async def test_uses_fallback_model_when_preferred_model_unavailable() -> None:
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


@pytest.mark.asyncio()
@pytest.mark.integration()
async def test_uses_environment_configured_model_for_chat() -> None:
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
    client.chat.completions.create.assert_called_once()
    assert client.chat.completions.create.call_args.kwargs["model"] == "gpt-4-turbo"

    # Clean up
    del os.environ["OPENAI_CHAT_MODEL"]


@pytest.mark.asyncio()
@pytest.mark.integration()
async def test_rejects_image_generation_when_no_data_returned() -> None:
    client = AsyncMock()
    client.images.generate.return_value = AsyncMock(data=[])
    repo = OpenAIAPIRepository(client)
    with pytest.raises(ValueError):
        await repo.generate_image("p")


@pytest.mark.asyncio()
@pytest.mark.integration()
async def test_rejects_image_generation_when_b64_json_is_none() -> None:
    """Test that None b64_json is handled gracefully."""
    client = AsyncMock()
    client.images.generate.return_value = AsyncMock(data=[AsyncMock(b64_json=None)])
    repo = OpenAIAPIRepository(client)
    with pytest.raises(ValueError, match="OpenAI did not return valid image data"):
        await repo.generate_image("prompt")


@pytest.mark.asyncio()
@pytest.mark.integration()
async def test_falls_back_to_dalle2_when_gpt_image_fails() -> None:
    """Test that image generation falls back to DALL-E 2 when gpt-image-1 fails."""
    client = AsyncMock()

    # First call (gpt-image-1) fails
    client.images.generate.side_effect = [
        Exception("gpt-image-1 not available"),
        AsyncMock(data=[AsyncMock(b64_json="aGVsbG8=")]),  # DALL-E 2 succeeds
    ]

    repo = OpenAIAPIRepository(client)
    result = await repo.generate_image("test prompt")

    # Should have called both models
    assert client.images.generate.call_count == 2

    # First call should be gpt-image-1
    first_call = client.images.generate.call_args_list[0]
    assert first_call.kwargs["model"] == "gpt-image-1"

    # Second call should be DALL-E 2
    second_call = client.images.generate.call_args_list[1]
    assert second_call.kwargs["model"] == "dall-e-2"
    assert second_call.kwargs["size"] == "512x512"  # DALL-E 2 max size

    # Should return the result
    assert isinstance(result, bytes)


@pytest.mark.asyncio()
@pytest.mark.integration()
async def test_enhance_prompt_raises_rate_limit_error() -> None:
    client = AsyncMock()
    client.chat.completions.create.side_effect = openai.RateLimitError(
        "rate limit",
        response=httpx.Response(429, request=httpx.Request("GET", "https://api.test")),
        body=None,
    )
    repo = OpenAIAPIRepository(client)
    with pytest.raises(RateLimitExceededError):
        await repo.enhance_prompt("ctx", "desc")


@pytest.mark.asyncio()
@pytest.mark.integration()
async def test_generate_image_raises_rate_limit_error() -> None:
    client = AsyncMock()
    client.images.generate.side_effect = [
        openai.RateLimitError(
            "rl",
            response=httpx.Response(
                429, request=httpx.Request("GET", "https://api.test")
            ),
            body=None,
        ),
        openai.RateLimitError(
            "rl",
            response=httpx.Response(
                429, request=httpx.Request("GET", "https://api.test")
            ),
            body=None,
        ),
    ]
    repo = OpenAIAPIRepository(client)
    with pytest.raises(RateLimitExceededError):
        await repo.generate_image("prompt")
