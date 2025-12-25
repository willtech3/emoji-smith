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
from shared.infrastructure.logging import log_event


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

    async def generate_image(
        self,
        prompt: str,
        num_images: int = 1,
        quality: str = "high",
        background: str = "transparent",
    ) -> list[bytes]:
        """Generate images using gpt-image-1.5 with fallback to gpt-image-1-mini.

        Args:
            prompt: Text description of the image to generate
            num_images: Number of images to generate (1-10, we cap at 4 for UX)
            quality: Rendering quality - "auto", "high", "medium", "low"
            background: Background type - "transparent", "opaque", "auto"

        Returns:
            List of image bytes (PNG format with alpha channel if transparent)
        """
        # Cap at 4 images for reasonable UX
        n = min(num_images, 4)
        is_fallback = False

        try:
            response = await self._client.images.generate(
                model="gpt-image-1.5",
                prompt=prompt,
                n=n,
                size="1024x1024",
                quality=quality,
                background=background,
                # GPT image models use output_format, not response_format
                output_format="png",
            )
        except openai.RateLimitError as exc:
            raise RateLimitExceededError(str(exc)) from exc
        except Exception as exc:
            self._logger.warning(
                "gpt-image-1.5 failed, falling back to gpt-image-1-mini: %s", exc
            )
            try:
                response = await self._client.images.generate(
                    model="gpt-image-1-mini",
                    prompt=prompt,
                    n=n,
                    size="1024x1024",
                    background=background,
                    # GPT image models use output_format
                    output_format="png",
                )
                is_fallback = True
            except openai.RateLimitError as rate_exc:
                raise RateLimitExceededError(str(rate_exc)) from rate_exc

        if not response.data:
            raise ValueError("OpenAI did not return image data")

        images = []
        for item in response.data:
            if item.b64_json:
                images.append(base64.b64decode(item.b64_json))

        log_event(
            self._logger,
            logging.INFO,
            "Image generated",
            event="model_generation",
            provider="openai",
            model=self._model,
            is_fallback=is_fallback,
        )
        return images
