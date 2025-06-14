"""OpenAI API repository implementation."""

# mypy: ignore-errors

import base64
import logging
from openai import AsyncOpenAI
from emojismith.domain.repositories.openai_repository import OpenAIRepository


class OpenAIAPIRepository(OpenAIRepository):
    """Concrete OpenAI repository using openai package with model fallback."""

    def __init__(self, client: AsyncOpenAI) -> None:
        self._client = client
        self._logger = logging.getLogger(__name__)
        self._preferred_models = ["o3", "gpt-4o", "gpt-4", "gpt-3.5-turbo"]
        self._model: str | None = None

    async def _select_model(self) -> str:
        if self._model:
            return self._model

        for name in self._preferred_models:
            try:
                await self._client.models.retrieve(name)
            except Exception as exc:  # pragma: no cover - network errors
                self._logger.info("Model %s unavailable: %s", name, exc)
                continue
            self._model = name
            self._logger.info("Using OpenAI model: %s", name)
            return name

        raise RuntimeError("No available OpenAI model for prompt enhancement")

    async def enhance_prompt(self, context: str, description: str) -> str:
        model = await self._select_model()
        response = await self._client.chat.completions.create(
            model=model,
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
