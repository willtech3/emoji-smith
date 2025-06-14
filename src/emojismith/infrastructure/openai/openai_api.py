"""OpenAI API repository implementation."""

# mypy: ignore-errors

from __future__ import annotations

import base64
import logging
from typing import Iterable, List
from openai import AsyncOpenAI
from emojismith.domain.repositories.openai_repository import OpenAIRepository


class OpenAIAPIRepository(OpenAIRepository):
    """Concrete OpenAI repository using openai package."""

    def __init__(
        self,
        client: AsyncOpenAI,
        model: str = "o3",
        fallback_models: Iterable[str] | None = None,
    ) -> None:
        self._client = client
        self._logger = logging.getLogger(__name__)
        self._model = model
        self._fallback_models: List[str] = list(
            fallback_models or ["gpt-4", "gpt-3.5-turbo"]
        )
        self._checked_model = False

    async def _ensure_model(self) -> None:
        if self._checked_model:
            return
        for name in [self._model, *self._fallback_models]:
            try:
                await self._client.models.retrieve(name)
            except Exception as exc:  # pragma: no cover - openai error
                self._logger.warning("Model %s unavailable: %s", name, exc)
                continue
            self._model = name
            break
        self._checked_model = True

    async def enhance_prompt(self, context: str, description: str) -> str:
        await self._ensure_model()
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": "Enhance emoji prompt"},
                {
                    "role": "user",
                    "content": f"Context: {context}\nDescription: {description}",
                },
            ],
        )
        return response.choices[0].message.content

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
