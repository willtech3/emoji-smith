"""Tests for OpenAIAPIRepository using HTTP-level mocking."""

import base64
import os
import json

import httpx
import pytest
import respx
from openai import AsyncOpenAI

from emojismith.infrastructure.openai.openai_api import OpenAIAPIRepository


@pytest.mark.asyncio
@respx.mock
async def test_enhances_prompt_with_ai_assistance() -> None:
    model_route = respx.get("https://api.openai.com/v1/models/o3").respond(
        200, json={"id": "o3"}
    )
    chat_route = respx.post("https://api.openai.com/v1/chat/completions").respond(
        200,
        json={
            "choices": [
                {
                    "message": {
                        "content": "ok",
                        "role": "assistant",
                    }
                }
            ]
        },
    )

    client = AsyncOpenAI(api_key="sk-test")
    repo = OpenAIAPIRepository(client, model="o3")
    result = await repo.enhance_prompt("ctx", "desc")

    assert result == "ok"
    assert model_route.called
    assert chat_route.called
    sent_json = json.loads(chat_route.calls[0].request.content.decode())
    assert sent_json["model"] == "o3"


@pytest.mark.asyncio
@respx.mock
async def test_uses_fallback_model_when_preferred_model_unavailable() -> None:
    respx.get("https://api.openai.com/v1/models/o3").respond(500)
    respx.get("https://api.openai.com/v1/models/gpt-4").respond(
        200, json={"id": "gpt-4"}
    )

    chat_route = respx.post("https://api.openai.com/v1/chat/completions").respond(
        200,
        json={"choices": [{"message": {"content": "fine"}}]},
    )

    client = AsyncOpenAI(api_key="sk-test")
    repo = OpenAIAPIRepository(client, model="o3", fallback_models=["gpt-4"])
    result = await repo.enhance_prompt("ctx", "desc")

    assert result == "fine"
    assert chat_route.called
    sent_json = json.loads(chat_route.calls[0].request.content.decode())
    assert sent_json["model"] == "gpt-4"


@pytest.mark.asyncio
@respx.mock
async def test_generates_emoji_image_from_text_prompt() -> None:
    png_b64 = base64.b64encode(b"test").decode()
    respx.post("https://api.openai.com/v1/images/generations").respond(
        200,
        json={"data": [{"b64_json": png_b64}]},
    )
    client = AsyncOpenAI(api_key="sk-test")
    repo = OpenAIAPIRepository(client)
    data = await repo.generate_image("prompt")
    assert isinstance(data, bytes)


@pytest.mark.asyncio
@respx.mock
async def test_uses_environment_configured_model_for_chat() -> None:
    """Repository should respect OPENAI_CHAT_MODEL environment variable."""
    os.environ["OPENAI_CHAT_MODEL"] = "gpt-4-turbo"

    respx.get("https://api.openai.com/v1/models/gpt-4-turbo").respond(
        200, json={"id": "gpt-4-turbo"}
    )
    chat_route = respx.post("https://api.openai.com/v1/chat/completions").respond(
        200,
        json={"choices": [{"message": {"content": "response"}}]},
    )

    client = AsyncOpenAI(api_key="sk-test")
    repo = OpenAIAPIRepository(client, model=os.getenv("OPENAI_CHAT_MODEL", "o3"))
    result = await repo.enhance_prompt("context", "description")

    assert result == "response"
    assert chat_route.called
    sent_json = json.loads(chat_route.calls[0].request.content.decode())
    assert sent_json["model"] == "gpt-4-turbo"

    del os.environ["OPENAI_CHAT_MODEL"]


@pytest.mark.asyncio
@respx.mock
async def test_rejects_image_generation_when_no_data_returned() -> None:
    respx.post("https://api.openai.com/v1/images/generations").respond(
        200, json={"data": []}
    )
    client = AsyncOpenAI(api_key="sk-test")
    repo = OpenAIAPIRepository(client)
    with pytest.raises(ValueError):
        await repo.generate_image("p")


@pytest.mark.asyncio
@respx.mock
async def test_rejects_image_generation_when_b64_json_is_none() -> None:
    """Gracefully handle null b64_json from API."""
    respx.post("https://api.openai.com/v1/images/generations").respond(
        200,
        json={"data": [{"b64_json": None}]},
    )
    client = AsyncOpenAI(api_key="sk-test")
    repo = OpenAIAPIRepository(client)
    with pytest.raises(ValueError, match="OpenAI did not return valid image data"):
        await repo.generate_image("prompt")


@pytest.mark.asyncio
@respx.mock
async def test_requests_base64_format_from_openai() -> None:
    """Image generation should request b64_json format."""
    png_b64 = base64.b64encode(b"hi").decode()
    route = respx.post("https://api.openai.com/v1/images/generations").respond(
        200,
        json={"data": [{"b64_json": png_b64}]},
    )
    client = AsyncOpenAI(api_key="sk-test")
    repo = OpenAIAPIRepository(client)

    await repo.generate_image("test prompt")

    assert route.called
    req_json = json.loads(route.calls[0].request.content.decode())
    assert req_json["response_format"] == "b64_json"


@pytest.mark.asyncio
@respx.mock
async def test_falls_back_to_dalle2_when_dalle3_fails() -> None:
    """Image generation should retry with DALL-E 2 when DALL-E 3 fails."""
    call_count = {"i": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        call_count["i"] += 1
        if call_count["i"] <= 3:
            raise httpx.HTTPError("dalle3 failed")
        return httpx.Response(
            200,
            json={"data": [{"b64_json": base64.b64encode(b"img").decode()}]},
        )

    respx.post("https://api.openai.com/v1/images/generations").mock(side_effect=handler)

    client = AsyncOpenAI(api_key="sk-test")
    repo = OpenAIAPIRepository(client)
    result = await repo.generate_image("test prompt")

    calls = respx.calls
    assert len(calls) >= 4
    first_json = json.loads(calls[0].request.content.decode())
    last_json = json.loads(calls[-1].request.content.decode())
    assert first_json["model"] == "dall-e-3"
    assert last_json["model"] == "dall-e-2"
    assert last_json["size"] == "512x512"
    assert isinstance(result, bytes)
