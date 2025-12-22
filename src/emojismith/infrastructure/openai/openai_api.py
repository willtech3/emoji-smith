"""OpenAI API repository implementation."""

# mypy: ignore-errors

from __future__ import annotations

import base64
import logging
from collections.abc import Iterable

import openai
from openai import AsyncOpenAI

from emojismith.domain.errors import RateLimitExceededError
from emojismith.domain.repositories.image_generation_repository import (
    ImageGenerationRepository,
)
from emojismith.domain.repositories.openai_repository import OpenAIRepository


class OpenAIAPIRepository(OpenAIRepository, ImageGenerationRepository):
    """Concrete OpenAI repository using openai package."""

    def __init__(
        self,
        client: AsyncOpenAI,
        model: str = "gpt-5",
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

        system_prompt = (
            "You are an expert at crafting prompts for OpenAI's gpt-image-1 model "
            "to create Slack emojis. Use the guidelines below.\n\n"
            "REQUIREMENTS:\n"
            "- Always mention a transparent background.\n"
            "- Optimize for 128x128 pixel Slack emoji display.\n"
            "- Keep shapes bold and high contrast for readability at tiny sizes.\n\n"
            "FORMAT:\n"
            '"[Style] [Subject] with [Key Features], transparent background, '
            'optimized for 128x128 pixel Slack emoji, [Additional Details]"\n\n'
            "STYLE OPTIONS:\n"
            "- Cartoon style for playful emojis\n"
            "- Minimalist flat design for professional contexts\n"
            "- Pixel art for retro themes\n"
            "- Realistic style for objects/foods\n\n"
            "PROMPT RULES:\n"
            "1. Simplify complex descriptions.\n"
            "2. Highlight distinctive features visible when small.\n"
            "3. Use vibrant contrasting colors.\n"
            "4. Avoid intricate detail.\n"
            "5. Incorporate message context when useful.\n"
            "6. Return only the final prompt text, "
            "without quotes or extra formatting.\n"
            "7. Use clear, concise phrasing suitable for "
            "an image generation prompt.\n\n"
            "EXAMPLES:\n"
            'Context: "Just shipped new feature" / Description: "rocket"\n'
            'Prompt: "Cartoon rocket launching with bright orange flames, '
            "transparent background, optimized for 128x128 pixel Slack emoji, "
            'bold outlines, vibrant colors"\n\n'
            'Context: "Team celebration" / Description: "party"\n'
            'Prompt: "Festive party popper bursting with confetti, transparent '
            "background, optimized for 128x128 pixel Slack emoji, cartoon style, "
            'bold colors"\n\n'
            'Context: "Coffee break" / Description: "tired"\n'
            'Prompt: "Sleepy face clutching coffee cup with rising steam, '
            "transparent background, optimized for 128x128 pixel Slack emoji, "
            'simple cartoon style, clear expression"\n'
        )

        try:
            response = await self._client.responses.create(
                model=self._model,
                input=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": (
                            "Context:\n```"
                            + context
                            + "```\nDescription:\n```"
                            + description
                            + "```"
                        ),
                    },
                ],
            )
        except (
            openai.RateLimitError
        ) as exc:  # pragma: no cover - network error simulated
            raise RateLimitExceededError(str(exc)) from exc
        return response.output_text

    async def generate_image(self, prompt: str) -> bytes:
        """Generate an image using gpt-image-1 with fallback to gpt-image-1-mini."""
        # Try gpt-image-1 first
        try:
            response = await self._client.images.generate(
                model="gpt-image-1",
                prompt=prompt,
                n=1,
                size="1024x1024",
                quality="high",
                background="transparent",  # Better for emojis
            )
        except (
            openai.RateLimitError
        ) as exc:  # pragma: no cover - network error simulated
            raise RateLimitExceededError(str(exc)) from exc
        except Exception as exc:
            self._logger.warning(
                "gpt-image-1 failed, falling back to gpt-image-1-mini: %s", exc
            )
            # Fallback to gpt-image-1-mini (fast, cost-effective)
            try:
                response = await self._client.images.generate(
                    model="gpt-image-1-mini",
                    prompt=prompt,
                    n=1,
                    size="1024x1024",
                    background="transparent",
                )
            except (
                openai.RateLimitError
            ) as rate_exc:  # pragma: no cover - network error simulated
                raise RateLimitExceededError(str(rate_exc)) from rate_exc
            except Exception as fallback_exc:
                self._logger.error(
                    "Both gpt-image-1 and gpt-image-1-mini failed: %s", fallback_exc
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
