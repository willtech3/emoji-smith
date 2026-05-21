"""OpenAI API repository implementation."""

# mypy: ignore-errors

from __future__ import annotations

import base64
import logging
import time
from collections.abc import Iterable

import openai
from openai import AsyncOpenAI

from emojismith.domain.errors import RateLimitExceededError
from emojismith.domain.repositories.image_generation_repository import (
    ImageGenerationRepository,
)
from emojismith.domain.repositories.openai_repository import OpenAIRepository
from shared.infrastructure.logging import log_event
from shared.infrastructure.telemetry.metrics import MetricsRecorder

OPENAI_IMAGE_MODEL = "gpt-image-2"
OPENAI_IMAGE_FALLBACK_MODELS = ["gpt-image-1.5", "gpt-image-1-mini"]


class OpenAIAPIRepository(OpenAIRepository, ImageGenerationRepository):
    """Concrete OpenAI repository using openai package."""

    def __init__(
        self,
        client: AsyncOpenAI,
        model: str = "gpt-5",
        fallback_models: Iterable[str] | None = None,
        metrics_recorder: MetricsRecorder | None = None,
    ) -> None:
        self._client = client
        self._logger = logging.getLogger(__name__)
        self._model = model
        self._fallback_models: list[str] = list(
            fallback_models or ["gpt-4", "gpt-3.5-turbo"]
        )
        self._checked_model = False
        self._metrics = metrics_recorder

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
            "You are an expert at crafting prompts for OpenAI GPT Image models, "
            "including gpt-image-2, to create custom Slack emojis. "
            "Use the guidelines below.\n\n"
            "REQUIREMENTS:\n"
            "- Describe a single centered emoji subject with a clean silhouette.\n"
            "- Optimize for 128x128 pixel Slack emoji display and readability "
            "at 20-32px.\n"
            "- Use bold shapes, simple composition, and high contrast colors.\n"
            "- Ask for a transparent background when supported; otherwise ask for an "
            "isolated subject on a plain, removable background.\n"
            "- Do not include text, letters, captions, or UI unless the user "
            "explicitly requests text.\n\n"
            "FORMAT:\n"
            '"[Style/medium] [single subject/action] with [2-3 distinctive visual '
            "features], centered icon composition, bold silhouette, optimized for "
            '128x128 Slack emoji, [background guidance]"\n\n'
            "STYLE OPTIONS:\n"
            "- Cartoon style for playful emojis\n"
            "- Minimalist flat design for professional contexts\n"
            "- Pixel art for retro themes\n"
            "- Realistic style for objects/foods\n\n"
            "PROMPT RULES:\n"
            "1. Turn vague or complex requests into one clear visual metaphor.\n"
            "2. Highlight distinctive features visible when small.\n"
            "3. Use concrete nouns, colors, materials, and emotion cues.\n"
            "4. Avoid busy backgrounds, tiny props, cropped subjects, and "
            "fine detail.\n"
            "5. Incorporate message context when useful.\n"
            "6. Return only the final prompt text, "
            "without quotes or extra formatting.\n"
            "7. Use clear, concise phrasing suitable for "
            "an image generation prompt.\n\n"
            "EXAMPLES:\n"
            'Context: "Just shipped new feature" / Description: "rocket"\n'
            'Prompt: "Cartoon rocket launching with bright orange flames, '
            "centered icon composition, bold silhouette, vibrant blue body and red "
            "fins, optimized for 128x128 Slack emoji, transparent background "
            'if supported"\n\n'
            'Context: "Team celebration" / Description: "party"\n'
            'Prompt: "Festive party popper bursting with a few large confetti pieces, '
            "simple cartoon style, centered icon composition, bold outlines, bright "
            'colors, optimized for 128x128 Slack emoji, isolated plain background"\n\n'
            'Context: "Coffee break" / Description: "tired"\n'
            'Prompt: "Sleepy face clutching coffee cup with rising steam, '
            "simple cartoon style, clear tired expression, bold silhouette, "
            'optimized for 128x128 Slack emoji, no text"\n'
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
        start_time = time.monotonic()
        n = min(num_images, 4)
        models_to_try = [OPENAI_IMAGE_MODEL, *OPENAI_IMAGE_FALLBACK_MODELS]
        used_model = OPENAI_IMAGE_MODEL
        is_fallback = False

        for index, candidate_model in enumerate(models_to_try):
            used_model = candidate_model
            is_fallback = index > 0
            request_background = background
            if candidate_model == OPENAI_IMAGE_MODEL and background == "transparent":
                # gpt-image-2 currently rejects transparent background requests.
                request_background = "auto"

            try:
                response = await self._client.images.generate(
                    model=used_model,
                    prompt=prompt,
                    n=n,
                    size="1024x1024",
                    quality=quality,
                    background=request_background,
                    output_format="png",
                )
                break
            except openai.RateLimitError as rate_exc:
                raise RateLimitExceededError(str(rate_exc)) from rate_exc
            except Exception as exc:
                if index == len(models_to_try) - 1:
                    raise
                next_model = models_to_try[index + 1]
                self._logger.warning(
                    "%s failed, falling back to %s: %s",
                    used_model,
                    next_model,
                    exc,
                )

        if not response.data:
            raise ValueError("OpenAI did not return image data")

        images = []
        for item in response.data:
            if item.b64_json:
                images.append(base64.b64decode(item.b64_json))

        duration_s = time.monotonic() - start_time
        if self._metrics is not None:
            self._metrics.record_emoji_generated(
                provider="openai",
                model=used_model,
                is_fallback=is_fallback,
                duration_s=duration_s,
            )

        log_event(
            self._logger,
            logging.INFO,
            "Image generated",
            event="model_generation",
            provider="openai",
            model=used_model,
            is_fallback=is_fallback,
        )
        return images
