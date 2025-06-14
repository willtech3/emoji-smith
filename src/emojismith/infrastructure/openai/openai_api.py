"""OpenAI API repository implementation."""

# mypy: ignore-errors

import base64
import logging
from openai import AsyncOpenAI
from emojismith.domain.repositories.openai_repository import OpenAIRepository


class OpenAIAPIRepository(OpenAIRepository):
    """Concrete OpenAI repository using openai package."""

    def __init__(self, client: AsyncOpenAI) -> None:
        self._client = client
        self._logger = logging.getLogger(__name__)

    async def enhance_prompt(self, context: str, description: str) -> str:
        response = await self._client.chat.completions.create(
            model="o3",
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
