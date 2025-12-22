import base64
import json

import httpx
import openai
import pytest

from emojismith.infrastructure.openai.openai_api import OpenAIAPIRepository


@pytest.mark.asyncio()
@pytest.mark.integration()
async def test_enhance_prompt_recorded() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.startswith("/v1/models"):
            return httpx.Response(200, json={})
        assert request.url.path == "/v1/responses"
        body = json.loads(request.content)
        # Responses API sends input list with user/system messages
        assert body["input"][1]["content"].startswith("Context")
        return httpx.Response(
            200,
            json={
                "output": [
                    {
                        "type": "message",
                        "role": "assistant",
                        "content": [{"type": "output_text", "text": "ok"}],
                    }
                ],
                "output_text": "ok",
            },
        )

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


@pytest.mark.asyncio()
@pytest.mark.integration()
async def test_generate_image_fallback() -> None:
    calls = []

    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.startswith("/v1/models"):
            return httpx.Response(200, json={})
        model = json.loads(request.content)["model"]
        calls.append(model)
        if model == "gpt-image-1":
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
    assert calls[0] == "gpt-image-1"
    assert calls[-1] == "gpt-image-1-mini"


@pytest.mark.asyncio()
@pytest.mark.integration()
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
