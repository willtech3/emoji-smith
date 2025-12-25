"""Unit tests for GeminiAPIRepository logging."""

import logging
from unittest.mock import AsyncMock, MagicMock

import pytest

from emojismith.infrastructure.google.gemini_api import GeminiAPIRepository


class TestGeminiAPIRepositoryLogging:
    """Test suite for GeminiAPIRepository logging."""

    @pytest.fixture()
    def mock_genai(self, monkeypatch):
        """Mock google.generativeai module."""
        mock = MagicMock()
        monkeypatch.setattr("emojismith.infrastructure.google.gemini_api.genai", mock)
        return mock

    @pytest.fixture()
    def repo(self, mock_genai):
        """Create a repository instance with mocked dependencies."""
        mock_client = MagicMock()
        return GeminiAPIRepository(client=mock_client)

    @pytest.mark.asyncio()
    async def test_generate_image_logs_model_generation(self, repo, caplog):
        """Verify model_generation event is logged on success."""
        # Setup mock client behavior

        # Configure the async response from _client.aio.models.generate_content
        mock_part = MagicMock()
        mock_part.inline_data.data = b"fake-image-data"

        mock_response = MagicMock()
        mock_response.parts = [mock_part]

        repo._client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        with caplog.at_level(logging.INFO):
            await repo.generate_image("test prompt")

        generation_logs = [
            r
            for r in caplog.records
            if hasattr(r, "event_data")
            and r.event_data.get("event") == "model_generation"
        ]
        assert len(generation_logs) == 1
        assert generation_logs[0].event_data["provider"] == "google_gemini"
        assert generation_logs[0].event_data["is_fallback"] is False

    @pytest.mark.asyncio()
    async def test_generate_image_logs_imagen_fallback(self, repo, caplog):
        """Verify fallback to Imagen logs correct event."""
        # Setup mock client behavior to simulate failure then success

        # Mock _generate_with_model to raise exception
        repo._generate_with_model = AsyncMock(side_effect=Exception("Gemini failed"))

        # Mock _generate_with_imagen to succeed
        repo._generate_with_imagen = AsyncMock(return_value=b"fallback-image")

        with caplog.at_level(logging.INFO):
            await repo.generate_image("test prompt")

        # Verify fallback log
        fallback_logs = [
            r
            for r in caplog.records
            if hasattr(r, "event_data")
            and r.event_data.get("event") == "model_generation"
            and r.event_data.get("is_fallback") is True
        ]

        assert len(fallback_logs) == 1
        assert fallback_logs[0].event_data["provider"] == "google_imagen"
        assert fallback_logs[0].event_data["model"] == "imagen-4-ultra-preview"
