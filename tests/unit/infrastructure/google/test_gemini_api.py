# ruff: noqa: I001
"""Unit tests for GeminiAPIRepository logging."""

import logging
import sys
import types
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

# Stub google modules to satisfy imports
google_module = types.ModuleType("google")
api_core = types.ModuleType("google.api_core")


class _ResourceExhaustedError(Exception):
    """Stubbed ResourceExhausted exception."""


class _TooManyRequestsError(Exception):
    """Stubbed TooManyRequests exception."""


api_core.exceptions = types.SimpleNamespace(
    ResourceExhausted=_ResourceExhaustedError, TooManyRequests=_TooManyRequestsError
)

google_module.__path__ = []

genai_module = types.ModuleType("google.genai")
types_module = types.SimpleNamespace(
    GenerateContentConfig=type(
        "GenerateContentConfig",
        (),
        {"__init__": lambda self, *args, **kwargs: None},
    ),
    ImageConfig=type(
        "ImageConfig",
        (),
        {"__init__": lambda self, *args, **kwargs: None},
    ),
    GenerateImagesConfig=type(
        "GenerateImagesConfig",
        (),
        {"__init__": lambda self, *args, **kwargs: None},
    ),
)

google_module.genai = genai_module
google_module.api_core = api_core
genai_module.types = types_module

sys.modules["google"] = google_module
sys.modules["google.api_core"] = api_core
sys.modules["google.api_core.exceptions"] = api_core.exceptions
sys.modules["google.genai"] = genai_module
sys.modules["google.genai.types"] = types_module

from emojismith.infrastructure.google.gemini_api import GeminiAPIRepository  # noqa: E402


@pytest.mark.asyncio()
async def test_generate_image_logs_model_generation(caplog):
    """Verify model_generation event is logged on success."""

    client = SimpleNamespace()
    client.aio = SimpleNamespace()
    client.aio.models = SimpleNamespace(
        generate_content=AsyncMock(
            return_value=SimpleNamespace(
                parts=[SimpleNamespace(inline_data=SimpleNamespace(data=b"data"))]
            )
        )
    )

    repo = GeminiAPIRepository(client)

    with caplog.at_level(logging.INFO):
        await repo.generate_image("test prompt")

    generation_logs = [
        record
        for record in caplog.records
        if getattr(record, "event_data", {}).get("event") == "model_generation"
    ]
    assert len(generation_logs) == 1
    assert generation_logs[0].event_data["provider"] == "google_gemini"
    assert generation_logs[0].event_data["model"] == "gemini-3-pro-image-preview"


@pytest.mark.asyncio()
async def test_generate_image_logs_imagen_fallback(caplog):
    """Verify Imagen fallback logs model_generation event."""

    client = SimpleNamespace()
    client.aio = SimpleNamespace()
    client.aio.models = SimpleNamespace(
        generate_content=AsyncMock(side_effect=Exception("gemini failure")),
        generate_images=AsyncMock(
            return_value=SimpleNamespace(
                generated_images=[
                    SimpleNamespace(
                        image=SimpleNamespace(image_bytes=b"fallback-bytes"),
                    )
                ]
            )
        ),
    )

    repo = GeminiAPIRepository(client)

    with caplog.at_level(logging.INFO):
        images = await repo.generate_image("prompt")

    assert images[0] == b"fallback-bytes"
    generation_logs = [
        record
        for record in caplog.records
        if getattr(record, "event_data", {}).get("event") == "model_generation"
    ]
    assert generation_logs
    assert any(
        log.event_data["provider"] == "google_imagen" and log.event_data["is_fallback"]
        for log in generation_logs
    )
