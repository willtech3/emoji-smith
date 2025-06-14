"""OpenAI API repository implementation."""

import base64
from openai import AsyncOpenAI

from emojismith.domain.repositories.openai_repository import OpenAIRepository


class OpenAIAPIRepository(OpenAIRepository):
    """Concrete implementation of OpenAIRepository using the OpenAI SDK."""

    def __init__(self, client: AsyncOpenAI) -> None:
        self._client = client

    async def optimize_prompt(self, context: str, description: str) -> str:
        response = await self._client.chat.completions.create(
            model="o3",
            messages=[
                {
                    "role": "system",
                    "content": "You help craft concise prompts for emoji generation.",
                },
                {
                    "role": "user",
                    "content": f"Context: {context}\nDescription: {description}",
                },
            ],
            max_tokens=60,
        )
        content = response.choices[0].message.content or ""
        return content.strip()

    async def generate_image(self, prompt: str) -> bytes:
        response = await self._client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="128x128",  # type: ignore[arg-type]
            response_format="b64_json",
        )
        b64_data = response.data[0].b64_json or ""  # type: ignore[index]
        return base64.b64decode(b64_data)
