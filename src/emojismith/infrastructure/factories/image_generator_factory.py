"""Factory for creating image generation repositories."""

from __future__ import annotations

from typing import TYPE_CHECKING

from google import genai
from openai import AsyncOpenAI

from emojismith.domain.factories.image_generator_factory import (
    ImageGeneratorFactory as ImageGeneratorFactoryProtocol,
)
from emojismith.domain.value_objects.image_provider import ImageProvider
from emojismith.infrastructure.google.gemini_api import GeminiAPIRepository
from emojismith.infrastructure.openai.openai_api import OpenAIAPIRepository

if TYPE_CHECKING:
    from emojismith.domain.repositories.image_generation_repository import (
        ImageGenerationRepository,
    )


class ImageGeneratorFactory(ImageGeneratorFactoryProtocol):
    """Factory to create the appropriate image generator based on provider.

    API keys are injected via constructor following DDD principles
    (no direct os.getenv access per CLAUDE.md guidelines).
    """

    def __init__(
        self,
        openai_api_key: str | None = None,
        google_api_key: str | None = None,
    ) -> None:
        """Initialize factory with API keys.

        Args:
            openai_api_key: OpenAI API key (required for OpenAI provider).
            google_api_key: Google API key (required for Gemini provider).
        """
        self._openai_api_key = openai_api_key
        self._google_api_key = google_api_key

    def create(self, provider: ImageProvider) -> ImageGenerationRepository:
        """Create an image generator for the specified provider.

        Args:
            provider: The image generation provider to use.

        Returns:
            An image generation repository instance.

        Raises:
            ValueError: If required API key is not configured.
        """
        if provider == ImageProvider.OPENAI:
            if not self._openai_api_key:
                raise ValueError("OPENAI_API_KEY required for OpenAI provider")
            openai_client = AsyncOpenAI(api_key=self._openai_api_key)
            return OpenAIAPIRepository(openai_client)

        elif provider == ImageProvider.GOOGLE_GEMINI:
            if not self._google_api_key:
                raise ValueError("GOOGLE_API_KEY required for Gemini provider")
            gemini_client = genai.Client(api_key=self._google_api_key)
            return GeminiAPIRepository(gemini_client)

        else:
            raise ValueError(f"Unsupported provider: {provider}")
