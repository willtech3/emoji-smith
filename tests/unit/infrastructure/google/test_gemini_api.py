"""Unit tests for GeminiAPIRepository logging."""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock, MagicMock

import pytest

from emojismith.infrastructure.google.gemini_api import GeminiAPIRepository


@pytest.mark.asyncio()
async def test_generate_image_logs_model_generation(caplog):
    """Verify model_generation event is logged on success."""
    client = MagicMock()
    repo = GeminiAPIRepository(client=client)
    repo._generate_with_model = AsyncMock(return_value=b"image-bytes")  # type: ignore[attr-defined]

    with caplog.at_level(logging.INFO):
        images = await repo.generate_image("test prompt")

    assert images == [b"image-bytes"]
    generation_logs = [
        r
        for r in caplog.records
        if hasattr(r, "event_data") and r.event_data.get("event") == "model_generation"
    ]
    assert len(generation_logs) == 1
    assert generation_logs[0].event_data["provider"] == "google_gemini"
    assert generation_logs[0].event_data["model"] == repo._model
    assert generation_logs[0].event_data["is_fallback"] is False


@pytest.mark.asyncio()
async def test_generate_image_logs_imagen_fallback(caplog):
    """Verify model_generation event is logged for Imagen fallback."""
    client = MagicMock()
    repo = GeminiAPIRepository(client=client)
    repo._generate_with_model = AsyncMock(side_effect=Exception("primary failed"))  # type: ignore[attr-defined]
    repo._generate_with_imagen = AsyncMock(return_value=b"fallback-image")  # type: ignore[attr-defined]

    with caplog.at_level(logging.INFO):
        images = await repo.generate_image("test prompt")

    assert images == [b"fallback-image"]
    generation_logs = [
        r
        for r in caplog.records
        if hasattr(r, "event_data") and r.event_data.get("event") == "model_generation"
    ]
    assert len(generation_logs) == 1
    assert generation_logs[0].event_data["provider"] == "google_imagen"
    assert generation_logs[0].event_data["model"] == repo._fallback_model
    assert generation_logs[0].event_data["is_fallback"] is True
