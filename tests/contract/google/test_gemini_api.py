"""Contract tests for GeminiAPIRepository."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from google.api_core import exceptions as google_exceptions

from emojismith.domain.errors import RateLimitExceededError
from emojismith.infrastructure.google.gemini_api import GeminiAPIRepository


@pytest.fixture()
def mock_gemini_client():
    """Create a mock Gemini client with async interface."""
    client = MagicMock()

    # Set up the async model interface
    async_models = MagicMock()
    async_models.generate_content = AsyncMock()
    async_models.generate_images = AsyncMock()  # Add Imagen API mock
    client.aio.models = async_models

    return client


@pytest.fixture()
def repository(mock_gemini_client):
    """Create repository with mocked client."""
    return GeminiAPIRepository(
        client=mock_gemini_client,
        model="gemini-3-pro-image-preview",
        fallback_model="imagen-4.0-ultra-generate-001",
    )


class TestGeminiAPIRepositoryGenerateImage:
    """Tests for GeminiAPIRepository.generate_image method."""

    @pytest.mark.asyncio()
    async def test_generate_image_when_successful_returns_list_of_bytes(
        self, repository, mock_gemini_client
    ):
        """Test successful image generation returns list of image bytes."""
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
        assert result == [expected_image_data]
        mock_gemini_client.aio.models.generate_content.assert_called_once()

    @pytest.mark.asyncio()
    async def test_generate_image_when_primary_fails_uses_imagen_fallback(
        self, repository, mock_gemini_client
    ):
        """Test Imagen fallback is used when primary Gemini model fails."""
        # Arrange
        expected_image_data = b"fallback_image_bytes"

        # Mock Imagen response
        mock_image = MagicMock()
        mock_image.image = MagicMock()
        mock_image.image.image_bytes = expected_image_data

        mock_imagen_response = MagicMock()
        mock_imagen_response.generated_images = [mock_image]

        # Primary fails, fallback succeeds
        mock_gemini_client.aio.models.generate_content.side_effect = Exception(
            "Primary model error"
        )
        mock_gemini_client.aio.models.generate_images.return_value = (
            mock_imagen_response
        )

        # Act
        result = await repository.generate_image("Test prompt")

        # Assert
        assert result == [expected_image_data]
        mock_gemini_client.aio.models.generate_content.assert_called_once()
        mock_gemini_client.aio.models.generate_images.assert_called_once()

    @pytest.mark.asyncio()
    async def test_generate_image_when_quota_exceeded_raises_rate_limit_error(
        self, repository, mock_gemini_client
    ):
        """Test rate limit error is raised when quota is exceeded."""
        # Arrange - use proper Google API exception type
        mock_gemini_client.aio.models.generate_content.side_effect = (
            google_exceptions.ResourceExhausted("Quota exceeded")
        )

        # Act & Assert
        with pytest.raises(RateLimitExceededError):
            await repository.generate_image("Test prompt")

    @pytest.mark.asyncio()
    async def test_generate_image_when_fallback_quota_exceeded_raises_rate_limit_error(
        self, repository, mock_gemini_client
    ):
        """Test rate limit error is raised when fallback quota is exceeded."""
        # Arrange - primary fails, fallback hits rate limit
        mock_gemini_client.aio.models.generate_content.side_effect = Exception(
            "Primary model error"
        )
        mock_gemini_client.aio.models.generate_images.side_effect = (
            google_exceptions.ResourceExhausted("Quota exceeded for fallback")
        )

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
        """Test ValueError is raised when both models return no image data."""
        # Arrange - primary returns empty, fallback also fails
        mock_response = MagicMock()
        mock_response.parts = []  # No parts returned

        mock_gemini_client.aio.models.generate_content.return_value = mock_response

        # Mock empty Imagen response after primary fails
        mock_imagen_response = MagicMock()
        mock_imagen_response.generated_images = []
        mock_gemini_client.aio.models.generate_images.return_value = (
            mock_imagen_response
        )

        # Act & Assert
        with pytest.raises(ValueError, match=r"(Gemini|Imagen) did not return"):
            await repository.generate_image("Test prompt")

    @pytest.mark.asyncio()
    async def test_generate_image_when_both_models_fail_raises_last_error(
        self, repository, mock_gemini_client
    ):
        """Test that when both models fail, the fallback error is raised."""
        # Arrange - both primary and Imagen fallback fail
        mock_gemini_client.aio.models.generate_content.side_effect = Exception(
            "Primary model unavailable"
        )
        mock_gemini_client.aio.models.generate_images.side_effect = Exception(
            "Imagen fallback unavailable"
        )

        # Act & Assert
        with pytest.raises(Exception, match="Imagen fallback unavailable"):
            await repository.generate_image("Test prompt")
