"""OpenAI API repository implementation."""

# mypy: ignore-errors

from __future__ import annotations

import base64
import logging
from collections.abc import Iterable

import openai
from openai import AsyncOpenAI

from emojismith.domain.errors import RateLimitExceededError
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
        self._fallback_models: list[str] = list(
            fallback_models or ["gpt-4", "gpt-3.5-turbo"]
        )
        self._checked_model = False

    async def _ensure_model(self) -> None:
        if self._checked_model:
            return

        original_model = self._model
        for name in [self._model, *self._fallback_models]:
            try:
                await self._client.models.retrieve(name)
                self._model = name
                if name != original_model:
                    self._logger.info(
                        "Using fallback model '%s' (primary model '%s' unavailable)",
                        name,
                        original_model,
                    )
                break
            except Exception as exc:
                self._logger.warning("Model %s unavailable: %s", name, exc)
                continue

        self._checked_model = True

    async def enhance_prompt(self, context: str, description: str) -> str:
        await self._ensure_model()

        system_prompt = """You are an expert at creating prompts for DALL-E image
generation specifically optimized for Slack emoji.

CRITICAL REQUIREMENTS:
- ALWAYS specify "transparent background" in every prompt
- Optimize for 128x128 pixel display size
- Focus on instant recognition at small sizes
- Use bold, clear shapes with high contrast

SLACK EMOJI TECHNICAL CONSTRAINTS:
- Display size: 128x128 pixels (though uploaded at higher resolution)
- Must work well as reactions (tiny 20x20 display)
- Transparent backgrounds are ESSENTIAL
- Maximum file size: 128KB
- Supported formats: PNG, JPG, GIF

PROMPT STRUCTURE TEMPLATE:
"[Style] [Subject] with [Key Features], transparent background,
optimized for 128x128 pixel Slack emoji, [Additional Details]"

STYLE OPTIONS (choose most appropriate):
- Cartoon/illustrated style - Best for fun, approachable emojis
- Minimalist flat design - Best for professional contexts
- Pixel art style - Best for retro/gaming themes
- Realistic style - Best for specific objects/foods

ENHANCEMENT RULES:
1. Simplify complex descriptions for clarity at small sizes
2. Emphasize distinctive features that remain visible when tiny
3. Use vibrant, contrasting colors for visibility
4. Avoid intricate details that disappear at 128x128
5. Include relevant context from the message when meaningful

EXAMPLES:
Input: Context: "Just shipped new feature", Description: "rocket"
Output: "Cartoon style rocket ship launching with bright orange flames
and smoke clouds, transparent background, optimized for 128x128 pixel
Slack emoji, bold outlines, vibrant colors"

Input: Context: "Team celebration", Description: "party"
Output: "Festive party popper with colorful confetti burst, transparent
background, optimized for 128x128 pixel Slack emoji, cartoon style with
bold colors and thick outlines"

Input: Context: "Coffee break", Description: "tired"
Output: "Sleepy face with coffee cup, half-closed eyes and steam swirls,
transparent background, optimized for 128x128 pixel Slack emoji, simple
cartoon style with clear expressions"

Remember: The emoji must be instantly recognizable at 20x20 pixels
while looking great at 128x128!"""

        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": f"Context: {context}\nDescription: {description}",
                    },
                ],
            )
        except (
            openai.RateLimitError
        ) as exc:  # pragma: no cover - network error simulated
            raise RateLimitExceededError(str(exc)) from exc
        return response.choices[0].message.content

    async def generate_image(self, prompt: str) -> bytes:
        """Generate an image using DALL-E 3 with fallback to DALL-E 2."""
        # Try DALL-E 3 first
        try:
            response = await self._client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                n=1,
                size="1024x1024",
                response_format="b64_json",
                quality="standard",
            )
        except (
            openai.RateLimitError
        ) as exc:  # pragma: no cover - network error simulated
            raise RateLimitExceededError(str(exc)) from exc
        except Exception as exc:
            self._logger.warning("DALL-E 3 failed, falling back to DALL-E 2: %s", exc)
            # Fallback to DALL-E 2
            try:
                response = await self._client.images.generate(
                    model="dall-e-2",
                    prompt=prompt,
                    n=1,
                    size="512x512",  # DALL-E 2 max size
                    response_format="b64_json",
                )
            except (
                openai.RateLimitError
            ) as rate_exc:  # pragma: no cover - network error simulated
                raise RateLimitExceededError(str(rate_exc)) from rate_exc
            except Exception as fallback_exc:
                self._logger.error(
                    "Both DALL-E 3 and DALL-E 2 failed: %s", fallback_exc
                )
                raise fallback_exc

        if not response.data:
            raise ValueError("OpenAI did not return image data")

        b64 = response.data[0].b64_json
        if b64 is None:
            raise ValueError("OpenAI did not return valid image data")
        if isinstance(b64, str):
            return base64.b64decode(b64)
        return b64
