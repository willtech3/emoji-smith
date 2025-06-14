"""OpenAI API repository implementation."""

# mypy: ignore-errors

import base64
import logging
from openai import AsyncOpenAI
from emojismith.domain.repositories.openai_repository import OpenAIRepository
from typing import List, Optional


class OpenAIAPIRepository(OpenAIRepository):
    """Concrete OpenAI repository using openai package."""

    def __init__(
        self,
        client: AsyncOpenAI,
        model: str = "o3",
        fallback_models: Optional[List[str]] = None,
    ) -> None:
        self._client = client
        self._logger = logging.getLogger(__name__)
        self._model = model
        self._fallback_models = fallback_models or ["gpt-4", "gpt-3.5-turbo"]

    async def enhance_prompt(self, context: str, description: str) -> str:
        messages = [
            {"role": "system", "content": "Enhance emoji prompt"},
            {
                "role": "user",
                "content": f"Context: {context}\nDescription: {description}",
            },
        ]
        last_exc: Exception | None = None
        for model in [self._model, *self._fallback_models]:
            try:
                response = await self._client.chat.completions.create(
                    model=model,
                    messages=messages,
                )
                if model != self._model:
                    self._logger.info("Falling back to OpenAI model %s", model)
                return response.choices[0].message.content
            except Exception as exc:  # pragma: no cover - fallback attempts
                self._logger.warning(
                    "OpenAI completion failed with model %s: %s", model, exc
                )
                last_exc = exc
        raise RuntimeError("All OpenAI models failed") from last_exc

    async def generate_image(self, prompt: str) -> bytes:
        """Generate an image using DALL-E 3 and return raw bytes."""
        try:
            response = await self._client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                n=1,
                size="1024x1024",
            )
        except Exception as exc:  # pragma: no cover - passthrough logging
            self._logger.error("OpenAI image generation failed: %s", exc)
            raise

        if not response.data:
            raise ValueError("OpenAI did not return image data")

        b64 = response.data[0].b64_json
        if isinstance(b64, str):
            return base64.b64decode(b64)
        return b64
