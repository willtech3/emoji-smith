import json
import httpx
import pytest
from openai import AsyncOpenAI

from emojismith.infrastructure.openai.openai_api import OpenAIAPIRepository


@pytest.mark.asyncio
async def test_enhance_prompt_request_contains_context_and_description() -> None:
    """Recorded response test verifying request payload for chat completion."""
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path.startswith("/v1/models"):
            return httpx.Response(200, json={"id": "o3"})
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "enhanced"}}]},
        )

    transport = httpx.MockTransport(handler)
    client = AsyncOpenAI(
        api_key="sk-test",
        base_url="http://openai.local/v1",
        http_client=httpx.AsyncClient(transport=transport),
    )
    repo = OpenAIAPIRepository(client)

    result = await repo.enhance_prompt("ctx", "desc")

    assert result == "enhanced"
    assert requests[-1].url.path.endswith("/chat/completions")
    body = json.loads(requests[-1].content.decode())
    assert body["messages"][1]["content"] == "Context: ctx\nDescription: desc"


@pytest.mark.asyncio
async def test_generate_image_request_and_response_decoding() -> None:
    """Recorded response test for image generation parameters and decoding."""
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(
            200,
            json={"data": [{"b64_json": "aGVsbG8="}]},
        )

    transport = httpx.MockTransport(handler)
    client = AsyncOpenAI(
        api_key="sk-test",
        base_url="http://openai.local/v1",
        http_client=httpx.AsyncClient(transport=transport),
    )
    repo = OpenAIAPIRepository(client)

    result = await repo.generate_image("prompt")

    assert result == b"hello"
    assert captured[0].url.path.endswith("/images/generations")
    payload = json.loads(captured[0].content.decode())
    assert payload["prompt"] == "prompt"
    assert payload["response_format"] == "b64_json"


@pytest.mark.asyncio
async def test_generate_image_raises_on_api_failure() -> None:
    """Ensure API errors propagate when both models fail."""

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "boom"})

    transport = httpx.MockTransport(handler)
    client = AsyncOpenAI(
        api_key="sk-test",
        base_url="http://openai.local/v1",
        http_client=httpx.AsyncClient(transport=transport),
    )
    repo = OpenAIAPIRepository(client)

    with pytest.raises(Exception):
        await repo.generate_image("oops")
