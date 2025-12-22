"""Tests for ImageGeneratorFactory."""

import pytest

from emojismith.domain.value_objects.image_provider import ImageProvider
from emojismith.infrastructure.factories.image_generator_factory import (
    ImageGeneratorFactory,
)
from emojismith.infrastructure.google.gemini_api import GeminiAPIRepository
from emojismith.infrastructure.openai.openai_api import OpenAIAPIRepository


class TestImageGeneratorFactoryCreate:
    """Tests for ImageGeneratorFactory.create method."""

    def test_create_when_openai_selected_returns_openai_repository(self):
        """Test that OpenAI provider returns OpenAIAPIRepository."""
        factory = ImageGeneratorFactory(
            openai_api_key="test-openai-key",
            google_api_key="test-google-key",
        )

        result = factory.create(ImageProvider.OPENAI)

        assert isinstance(result, OpenAIAPIRepository)

    def test_create_when_gemini_selected_returns_gemini_repository(self):
        """Test that Gemini provider returns GeminiAPIRepository."""
        factory = ImageGeneratorFactory(
            openai_api_key="test-openai-key",
            google_api_key="test-google-key",
        )

        result = factory.create(ImageProvider.GOOGLE_GEMINI)

        assert isinstance(result, GeminiAPIRepository)

    def test_create_when_openai_key_missing_raises_value_error(self):
        """Test that missing OpenAI key raises ValueError."""
        factory = ImageGeneratorFactory(
            openai_api_key=None,
            google_api_key="test-google-key",
        )

        with pytest.raises(ValueError, match="OPENAI_API_KEY required"):
            factory.create(ImageProvider.OPENAI)

    def test_create_when_google_key_missing_raises_value_error(self):
        """Test that missing Google key raises ValueError."""
        factory = ImageGeneratorFactory(
            openai_api_key="test-openai-key",
            google_api_key=None,
        )

        with pytest.raises(ValueError, match="GOOGLE_API_KEY required"):
            factory.create(ImageProvider.GOOGLE_GEMINI)

    def test_create_when_both_keys_present_can_create_either_provider(self):
        """Test that factory can create both providers when both keys present."""
        factory = ImageGeneratorFactory(
            openai_api_key="test-openai-key",
            google_api_key="test-google-key",
        )

        openai_repo = factory.create(ImageProvider.OPENAI)
        gemini_repo = factory.create(ImageProvider.GOOGLE_GEMINI)

        assert isinstance(openai_repo, OpenAIAPIRepository)
        assert isinstance(gemini_repo, GeminiAPIRepository)

    def test_create_when_only_openai_key_can_create_openai_provider(self):
        """Test that factory can create OpenAI with only OpenAI key."""
        factory = ImageGeneratorFactory(
            openai_api_key="test-openai-key",
            google_api_key=None,
        )

        result = factory.create(ImageProvider.OPENAI)

        assert isinstance(result, OpenAIAPIRepository)

    def test_create_when_only_google_key_can_create_gemini_provider(self):
        """Test that factory can create Gemini with only Google key."""
        factory = ImageGeneratorFactory(
            openai_api_key=None,
            google_api_key="test-google-key",
        )

        result = factory.create(ImageProvider.GOOGLE_GEMINI)

        assert isinstance(result, GeminiAPIRepository)


class TestImageGeneratorFactoryInit:
    """Tests for ImageGeneratorFactory initialization."""

    def test_init_with_no_keys_succeeds(self):
        """Test that factory can be initialized with no keys."""
        factory = ImageGeneratorFactory()

        assert factory._openai_api_key is None
        assert factory._google_api_key is None

    def test_init_with_both_keys_stores_them(self):
        """Test that factory stores provided keys."""
        factory = ImageGeneratorFactory(
            openai_api_key="openai-key",
            google_api_key="google-key",
        )

        assert factory._openai_api_key == "openai-key"
        assert factory._google_api_key == "google-key"
