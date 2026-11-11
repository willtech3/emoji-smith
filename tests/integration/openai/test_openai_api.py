"""Tests for OpenAIAPIRepository."""

import re
from unittest.mock import AsyncMock

import httpx
import openai
import pytest

from emojismith.domain.errors import (
    ImageGenerationRejectedError,
    RateLimitExceededError,
)
from emojismith.infrastructure.openai.openai_api import OpenAIAPIRepository


@pytest.mark.asyncio()
@pytest.mark.integration()
async def test_enhances_prompt_with_ai_assistance() -> None:
    client = AsyncMock()
    client.responses.create.return_value = AsyncMock(output_text="ok")
    repo = OpenAIAPIRepository(client)
    result = await repo.enhance_prompt("ctx", "desc")
    assert result == "ok"
    client.responses.create.assert_called_once()


@pytest.mark.asyncio()
@pytest.mark.integration()
async def test_enhance_prompt_uses_comprehensive_system_prompt() -> None:
    """Test that enhance_prompt uses a comprehensive system prompt for gpt-image."""
    client = AsyncMock()
    client.responses.create.return_value = AsyncMock(output_text="enhanced prompt")
    repo = OpenAIAPIRepository(client)

    context = "Team celebration"
    description = "party popper emoji"

    result = await repo.enhance_prompt(context, description)

    # Verify the API was called
    assert result == "enhanced prompt"
    client.responses.create.assert_called_once()

    # Extract the system prompt used
    call_args = client.responses.create.call_args
    input_msgs = call_args.kwargs["input"]
    system_prompt = input_msgs[0]["content"] if isinstance(input_msgs, list) else None

    # Verify the system prompt contains key requirements for emoji generation
    assert "transparent background" in system_prompt.lower()
    assert "128x128" in system_prompt
    assert "slack" in system_prompt.lower()
    assert "emoji" in system_prompt.lower()
    assert "gpt-image" in system_prompt.lower()
    assert "untrusted" in system_prompt.lower()
    assert (
        len(system_prompt) > 100
    )  # Should be comprehensive, not just "Enhance emoji prompt"


@pytest.mark.asyncio()
@pytest.mark.integration()
async def test_uses_fallback_model_when_preferred_model_unavailable() -> None:
    client = AsyncMock()
    client.models.retrieve = AsyncMock(side_effect=[Exception(), None])
    client.responses.create.return_value = AsyncMock(output_text="fine")
    repo = OpenAIAPIRepository(client, model="o3", fallback_models=["gpt-4"])
    result = await repo.enhance_prompt("ctx", "desc")
    assert result == "fine"
    client.responses.create.assert_called_once()
    assert client.responses.create.call_args.kwargs["model"] == "gpt-4"


@pytest.mark.asyncio()
@pytest.mark.integration()
async def test_uses_environment_configured_model_for_chat() -> None:
    """Test that repository respects OPENAI_CHAT_MODEL from environment."""
    import os

    # Set environment variable
    os.environ["OPENAI_CHAT_MODEL"] = "gpt-4-turbo"

    client = AsyncMock()
    client.models.retrieve = AsyncMock(return_value=None)
    client.responses.create.return_value = AsyncMock(output_text="response")

    # Create repository with environment model
    repo = OpenAIAPIRepository(client, model=os.getenv("OPENAI_CHAT_MODEL", "o3"))
    result = await repo.enhance_prompt("context", "description")

    # Verify it uses the environment-configured model
    assert result == "response"
    client.responses.create.assert_called_once()
    assert client.responses.create.call_args.kwargs["model"] == "gpt-4-turbo"

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
    """A successful-looking response without image bytes must fail the job."""
    client = AsyncMock()
    client.images.generate.return_value = AsyncMock(data=[AsyncMock(b64_json=None)])
    repo = OpenAIAPIRepository(client)
    with pytest.raises(ValueError, match="decodable image data"):
        await repo.generate_image("prompt")


@pytest.mark.asyncio()
@pytest.mark.integration()
async def test_generate_image_uses_gpt_image_2_6_sunburst_with_supported_background():
    """Use the latest high-end OpenAI image model with native transparency."""
    client = AsyncMock()
    client.images.generate.return_value = AsyncMock(
        data=[AsyncMock(b64_json="aGVsbG8=")]
    )
    repo = OpenAIAPIRepository(client)

    result = await repo.generate_image("test prompt", background="transparent")

    assert result == [b"hello"]
    client.images.generate.assert_called_once()
    client.images.generate.assert_awaited_once()
    call = client.images.generate.call_args
    assert call.kwargs["model"] == "gpt-image-2.6-sunburst"
    assert call.kwargs["size"] == "1024x1024"
    assert call.kwargs["n"] == 1
    assert call.kwargs["quality"] == "high"
    assert call.kwargs["background"] == "transparent"
    assert call.kwargs["output_format"] == "png"


@pytest.mark.asyncio()
@pytest.mark.integration()
async def test_does_not_fall_back_to_deprecated_image_models() -> None:
    """A gpt-image-2.6-sunburst failure must not route work to another model."""
    client = AsyncMock()
    client.images.generate.side_effect = Exception("gpt-image-2.6-sunburst unavailable")

    repo = OpenAIAPIRepository(client)
    with pytest.raises(
        Exception, match=re.escape("gpt-image-2.6-sunburst unavailable")
    ):
        await repo.generate_image("test prompt")

    client.images.generate.assert_awaited_once()
    assert client.images.generate.call_args.kwargs["model"] == "gpt-image-2.6-sunburst"


@pytest.mark.asyncio()
@pytest.mark.integration()
async def test_enhance_prompt_raises_rate_limit_error() -> None:
    client = AsyncMock()
    client.responses.create.side_effect = openai.RateLimitError(
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


def _bad_request(code: str) -> openai.BadRequestError:
    request = httpx.Request("POST", "https://api.openai.com/v1/images/generations")
    return openai.BadRequestError(
        "bad request",
        response=httpx.Response(400, request=request),
        body={"code": code, "message": "bad request"},
    )


@pytest.mark.asyncio()
@pytest.mark.integration()
async def test_generate_image_when_transparency_rejected_retries_with_auto() -> None:
    """A model that refuses transparency must still produce an emoji."""
    client = AsyncMock()
    client.images.generate.side_effect = [
        _bad_request("invalid_value"),
        AsyncMock(data=[AsyncMock(b64_json="aGVsbG8=")]),
    ]
    repo = OpenAIAPIRepository(client)

    result = await repo.generate_image("test prompt", background="transparent")

    assert result == [b"hello"]
    backgrounds = [
        call.kwargs["background"] for call in client.images.generate.call_args_list
    ]
    assert backgrounds == ["transparent", "auto"]


@pytest.mark.asyncio()
@pytest.mark.integration()
async def test_generate_image_when_opaque_request_rejected_does_not_retry() -> None:
    client = AsyncMock()
    client.images.generate.side_effect = _bad_request("invalid_value")
    repo = OpenAIAPIRepository(client)

    with pytest.raises(openai.BadRequestError):
        await repo.generate_image("test prompt", background="opaque")

    client.images.generate.assert_awaited_once()


@pytest.mark.asyncio()
@pytest.mark.integration()
async def test_generate_image_when_moderation_blocks_raises_rejected_error() -> None:
    """Moderation refusals are permanent, so they must not look retryable."""
    client = AsyncMock()
    client.images.generate.side_effect = _bad_request("moderation_blocked")
    repo = OpenAIAPIRepository(client)

    with pytest.raises(ImageGenerationRejectedError):
        await repo.generate_image("test prompt", background="transparent")

    client.images.generate.assert_awaited_once()


@pytest.mark.asyncio()
@pytest.mark.integration()
async def test_enhance_prompt_defaults_to_current_chat_models() -> None:
    """Retired chat models must not be the default or the fallbacks."""
    client = AsyncMock()
    client.models.retrieve.side_effect = [Exception("unavailable"), None]
    client.responses.create.return_value = AsyncMock(output_text="ok")
    repo = OpenAIAPIRepository(client)

    await repo.enhance_prompt("ctx", "desc")

    checked = [call.args[0] for call in client.models.retrieve.call_args_list]
    assert checked == ["gpt-6.1-sol", "gpt-6.1-terra"]
    assert client.responses.create.call_args.kwargs["model"] == "gpt-6.1-terra"
