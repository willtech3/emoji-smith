import base64
import json
import httpx
import openai
import pytest
import asyncio

from emojismith.infrastructure.openai.openai_api import OpenAIAPIRepository


@pytest.mark.asyncio
async def test_enhance_prompt_recorded() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.startswith("/v1/models"):
            return httpx.Response(200, json={})
        assert request.url.path == "/v1/chat/completions"
        body = json.loads(request.content)
        assert body["messages"][1]["content"].startswith("Context")
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    transport = httpx.MockTransport(handler)
    client = openai.AsyncOpenAI(
        api_key="sk-test",
        http_client=httpx.AsyncClient(
            transport=transport, base_url="https://api.openai.com/v1"
        ),
    )
    repo = OpenAIAPIRepository(client)
    result = await repo.enhance_prompt("context", "description")
    assert result == "ok"


@pytest.mark.asyncio
async def test_generate_image_fallback() -> None:
    calls = []

    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.startswith("/v1/models"):
            return httpx.Response(200, json={})
        model = json.loads(request.content)["model"]
        calls.append(model)
        if model == "dall-e-3":
            return httpx.Response(500)
        b64 = base64.b64encode(b"img").decode()
        return httpx.Response(200, json={"data": [{"b64_json": b64}]})

    transport = httpx.MockTransport(handler)
    client = openai.AsyncOpenAI(
        api_key="sk-test",
        http_client=httpx.AsyncClient(
            transport=transport, base_url="https://api.openai.com/v1"
        ),
    )
    repo = OpenAIAPIRepository(client)
    result = await repo.generate_image("prompt")
    assert result == b"img"
    assert calls[0] == "dall-e-3"
    assert calls[-1] == "dall-e-2"


@pytest.mark.asyncio
async def test_generate_image_handles_invalid_response() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.startswith("/v1/models"):
            return httpx.Response(200, json={})
        return httpx.Response(200, json={"data": []})

    transport = httpx.MockTransport(handler)
    client = openai.AsyncOpenAI(
        api_key="sk-test",
        http_client=httpx.AsyncClient(
            transport=transport, base_url="https://api.openai.com/v1"
        ),
    )
    repo = OpenAIAPIRepository(client)
    with pytest.raises(ValueError):
        await repo.generate_image("prompt")


@pytest.mark.asyncio
async def test_enhance_prompt_rate_limit_error() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.startswith("/v1/models"):
            return httpx.Response(200, json={})
        return httpx.Response(429)

    transport = httpx.MockTransport(handler)
    client = openai.AsyncOpenAI(
        api_key="sk-test",
        http_client=httpx.AsyncClient(
            transport=transport, base_url="https://api.openai.com/v1"
        ),
    )
    repo = OpenAIAPIRepository(client)
    with pytest.raises(openai.RateLimitError):
        await repo.enhance_prompt("context", "description")


@pytest.mark.asyncio
async def test_generate_image_timeout() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        await asyncio.sleep(1)
        return httpx.Response(
            200, json={"data": [{"b64_json": base64.b64encode(b"img").decode()}]}
        )

    transport = httpx.MockTransport(handler)
    client = openai.AsyncOpenAI(
        api_key="sk-test",
        http_client=httpx.AsyncClient(
            transport=transport, base_url="https://api.openai.com/v1"
        ),
    )
    repo = OpenAIAPIRepository(client)
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(repo.generate_image("prompt"), timeout=0.1)
