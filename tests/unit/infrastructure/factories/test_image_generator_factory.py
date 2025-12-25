"""Tests for ImageGeneratorFactory."""

# ruff: noqa: I001

import sys
import types
import pytest

from emojismith.domain.value_objects.image_provider import ImageProvider
from emojismith.infrastructure.factories.image_generator_factory import (
    ImageGeneratorFactory,
)
from emojismith.infrastructure.google.gemini_api import GeminiAPIRepository
from emojismith.infrastructure.openai.openai_api import OpenAIAPIRepository

google_module = types.ModuleType("google")
api_core = types.ModuleType("google.api_core")
api_core.exceptions = types.SimpleNamespace(
    ResourceExhausted=Exception, TooManyRequests=Exception
)
google_module.__path__ = []
genai_module = types.ModuleType("google.genai")
types_module = types.ModuleType("google.genai.types")


class _GenerateContentConfig:
    def __init__(self, *args, **kwargs) -> None:
        pass


class _ImageConfig:
    def __init__(self, *args, **kwargs) -> None:
        pass


class _GenerateImagesConfig:
    def __init__(self, *args, **kwargs) -> None:
        pass


types_module.GenerateContentConfig = _GenerateContentConfig
types_module.ImageConfig = _ImageConfig
types_module.GenerateImagesConfig = _GenerateImagesConfig


class _GenaiClient:
    def __init__(self, *args, **kwargs) -> None:
        pass


genai_module.Client = _GenaiClient
genai_module.types = types_module
google_module.api_core = api_core
google_module.genai = genai_module
sys.modules["google"] = google_module
sys.modules["google.api_core"] = api_core
sys.modules["google.api_core.exceptions"] = api_core.exceptions
sys.modules["google.genai"] = genai_module
sys.modules["google.genai.types"] = types_module


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
