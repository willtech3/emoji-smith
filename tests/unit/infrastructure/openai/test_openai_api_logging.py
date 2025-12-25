"""Tests for OpenAIAPIRepository structured logging."""

from __future__ import annotations

import logging
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from emojismith.infrastructure.openai.openai_api import OpenAIAPIRepository


@pytest.mark.asyncio()
async def test_generate_image_logs_model_generation_primary(caplog) -> None:
    """Verify model_generation is logged for the primary OpenAI model."""
    client = MagicMock()
    client.images = MagicMock()
    client.images.generate = AsyncMock(
        return_value=SimpleNamespace(data=[SimpleNamespace(b64_json="aGVsbG8=")])
    )

    repository = OpenAIAPIRepository(client, model="gpt-image-1.5")

    with caplog.at_level(logging.INFO):
        await repository.generate_image("test prompt")

    generation_logs = [
        record
        for record in caplog.records
        if getattr(record, "event_data", {}).get("event") == "model_generation"
    ]

    assert len(generation_logs) == 1
    assert generation_logs[0].event_data["provider"] == "openai"
    assert generation_logs[0].event_data["model"] == "gpt-image-1.5"
    assert generation_logs[0].event_data["is_fallback"] is False


@pytest.mark.asyncio()
async def test_generate_image_logs_model_generation_fallback(caplog) -> None:
    """Verify model_generation is logged with fallback metadata when primary fails."""
    client = MagicMock()
    client.images = MagicMock()
    client.images.generate = AsyncMock(
        side_effect=[
            Exception("primary failed"),
            SimpleNamespace(data=[SimpleNamespace(b64_json="aGVsbG8=")]),
        ]
    )

    repository = OpenAIAPIRepository(client, model="gpt-image-1.5")

    with caplog.at_level(logging.INFO):
        await repository.generate_image("test prompt")

    generation_logs = [
        record
        for record in caplog.records
        if getattr(record, "event_data", {}).get("event") == "model_generation"
    ]

    assert len(generation_logs) == 1
    assert generation_logs[0].event_data["provider"] == "openai"
    assert generation_logs[0].event_data["model"] == "gpt-image-1-mini"
    assert generation_logs[0].event_data["is_fallback"] is True
