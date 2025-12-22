"""Google Gemini API repository implementation."""

from __future__ import annotations

import logging

from google import genai
from google.genai import types

from emojismith.domain.errors import RateLimitExceededError
from emojismith.domain.repositories.image_generation_repository import (
    ImageGenerationRepository,
)


class GeminiAPIRepository(ImageGenerationRepository):
    """Concrete Gemini repository for image generation.

    Uses native async via client.aio for optimal performance.
    """

    def __init__(
        self,
        client: genai.Client,
        model: str = "gemini-3-pro-image-preview",
        fallback_model: str = "gemini-2.5-flash-image",
    ) -> None:
        self._client = client
        self._logger = logging.getLogger(__name__)
        self._model = model
        self._fallback_model = fallback_model

    async def _generate_with_model(self, prompt: str, model: str) -> bytes:
        """Generate image with specified model using native async."""
        response = await self._client.aio.models.generate_content(
            model=model,
            contents=prompt,  # String is supported (list optional for multi-modal)
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],  # Required for image output
                image_config=types.ImageConfig(
                    aspect_ratio="1:1",  # Square for emoji
                ),
            ),
        )

        if response.parts is not None:
            for part in response.parts:
                if part.inline_data and part.inline_data.data is not None:
                    return bytes(part.inline_data.data)

        raise ValueError("Gemini did not return image data")

    async def generate_image(self, prompt: str) -> bytes:
        """Generate image using Gemini with fallback."""
        try:
            return await self._generate_with_model(prompt, self._model)
        except Exception as exc:
            error_str = str(exc).lower()
            if "rate" in error_str or "quota" in error_str:
                raise RateLimitExceededError(str(exc)) from exc

            self._logger.warning(
                "%s failed, falling back to %s: %s",
                self._model,
                self._fallback_model,
                exc,
            )

            try:
                return await self._generate_with_model(prompt, self._fallback_model)
            except Exception as fallback_exc:
                error_str = str(fallback_exc).lower()
                if "rate" in error_str or "quota" in error_str:
                    raise RateLimitExceededError(str(fallback_exc)) from fallback_exc
                raise fallback_exc
