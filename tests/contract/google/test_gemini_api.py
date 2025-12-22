"""Contract tests for GeminiAPIRepository."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from emojismith.domain.errors import RateLimitExceededError
from emojismith.infrastructure.google.gemini_api import GeminiAPIRepository


@pytest.fixture()
def mock_gemini_client():
    """Create a mock Gemini client with async interface."""
    client = MagicMock()

    # Set up the async model interface
    async_models = MagicMock()
    async_models.generate_content = AsyncMock()
    client.aio.models = async_models

    return client


@pytest.fixture()
def repository(mock_gemini_client):
    """Create repository with mocked client."""
    return GeminiAPIRepository(
        client=mock_gemini_client,
        model="gemini-3-pro-image-preview",
        fallback_model="gemini-2.5-flash-image",
    )


class TestGeminiAPIRepositoryGenerateImage:
    """Tests for GeminiAPIRepository.generate_image method."""

    @pytest.mark.asyncio()
    async def test_generate_image_when_successful_returns_bytes(
        self, repository, mock_gemini_client
    ):
        """Test successful image generation returns image bytes."""
        # Arrange
        expected_image_data = b"fake_image_bytes"
        mock_part = MagicMock()
        mock_part.inline_data = MagicMock()
        mock_part.inline_data.data = expected_image_data

        mock_response = MagicMock()
        mock_response.parts = [mock_part]

        mock_gemini_client.aio.models.generate_content.return_value = mock_response

        # Act
        result = await repository.generate_image("Test prompt")

        # Assert
        assert result == expected_image_data
        mock_gemini_client.aio.models.generate_content.assert_called_once()

    @pytest.mark.asyncio()
    async def test_generate_image_when_primary_fails_uses_fallback(
        self, repository, mock_gemini_client
    ):
        """Test fallback model is used when primary model fails."""
        # Arrange
        expected_image_data = b"fallback_image_bytes"
        mock_part = MagicMock()
        mock_part.inline_data = MagicMock()
        mock_part.inline_data.data = expected_image_data

        mock_response = MagicMock()
        mock_response.parts = [mock_part]

        # First call fails, second call succeeds
        mock_gemini_client.aio.models.generate_content.side_effect = [
            Exception("Primary model error"),
            mock_response,
        ]

        # Act
        result = await repository.generate_image("Test prompt")

        # Assert
        assert result == expected_image_data
        assert mock_gemini_client.aio.models.generate_content.call_count == 2

    @pytest.mark.asyncio()
    async def test_generate_image_when_quota_exceeded_raises_rate_limit_error(
        self, repository, mock_gemini_client
    ):
        """Test rate limit error is raised when quota is exceeded."""
        # Arrange
        mock_gemini_client.aio.models.generate_content.side_effect = Exception(
            "Rate limit exceeded: quota exhausted"
        )

        # Act & Assert
        with pytest.raises(RateLimitExceededError):
            await repository.generate_image("Test prompt")

    @pytest.mark.asyncio()
    async def test_generate_image_when_fallback_quota_exceeded_raises_rate_limit_error(
        self, repository, mock_gemini_client
    ):
        """Test rate limit error is raised when fallback quota is exceeded."""
        # Arrange
        mock_gemini_client.aio.models.generate_content.side_effect = [
            Exception("Primary model error"),
            Exception("Quota exceeded for fallback"),
        ]

        # Act & Assert
        with pytest.raises(RateLimitExceededError):
            await repository.generate_image("Test prompt")

    @pytest.mark.asyncio()
    async def test_generate_image_uses_native_async_client(
        self, repository, mock_gemini_client
    ):
        """Test that the native async interface (client.aio) is used."""
        # Arrange
        expected_image_data = b"fake_image_bytes"
        mock_part = MagicMock()
        mock_part.inline_data = MagicMock()
        mock_part.inline_data.data = expected_image_data

        mock_response = MagicMock()
        mock_response.parts = [mock_part]

        mock_gemini_client.aio.models.generate_content.return_value = mock_response

        # Act
        await repository.generate_image("Test prompt")

        # Assert - verify the async interface was called
        mock_gemini_client.aio.models.generate_content.assert_called_once()
        # The call should include response_modalities for image output
        call_kwargs = mock_gemini_client.aio.models.generate_content.call_args
        assert call_kwargs is not None

    @pytest.mark.asyncio()
    async def test_generate_image_when_no_image_data_raises_value_error(
        self, repository, mock_gemini_client
    ):
        """Test ValueError is raised when Gemini returns no image data."""
        # Arrange
        mock_response = MagicMock()
        mock_response.parts = []  # No parts returned

        mock_gemini_client.aio.models.generate_content.return_value = mock_response

        # Act & Assert
        with pytest.raises(ValueError, match="Gemini did not return image data"):
            await repository.generate_image("Test prompt")

    @pytest.mark.asyncio()
    async def test_generate_image_when_both_models_fail_raises_last_error(
        self, repository, mock_gemini_client
    ):
        """Test that when both models fail, the fallback error is raised."""
        # Arrange
        mock_gemini_client.aio.models.generate_content.side_effect = [
            Exception("Primary model unavailable"),
            Exception("Fallback model unavailable"),
        ]

        # Act & Assert
        with pytest.raises(Exception, match="Fallback model unavailable"):
            await repository.generate_image("Test prompt")
