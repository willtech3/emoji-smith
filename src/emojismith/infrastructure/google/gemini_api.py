"""Google Gemini API repository implementation."""

from __future__ import annotations

import logging
import time

from google import genai
from google.api_core import exceptions as google_exceptions
from google.genai import types

from emojismith.domain.errors import RateLimitExceededError
from emojismith.domain.repositories.image_generation_repository import (
    ImageGenerationRepository,
)
from emojismith.domain.repositories.prompt_enhancer_repository import (
    PromptEnhancerRepository,
)
from shared.infrastructure.logging import log_event
from shared.infrastructure.telemetry.metrics import MetricsRecorder


class GeminiAPIRepository(ImageGenerationRepository, PromptEnhancerRepository):
    """Concrete Gemini repository for image generation and prompt enhancement.

    Uses native async via client.aio for optimal performance.
    Implements both ImageGenerationRepository and PromptEnhancerRepository protocols.
    """

    def __init__(
        self,
        client: genai.Client,
        model: str = "gemini-3-pro-image-preview",
        fallback_model: str = "imagen-4.0-ultra-generate-001",
        text_model: str = "gemini-3-flash-preview",
        metrics_recorder: MetricsRecorder | None = None,
    ) -> None:
        self._client = client
        self._logger = logging.getLogger(__name__)
        self._model = model
        self._fallback_model = fallback_model
        self._text_model = text_model
        self._metrics = metrics_recorder

    def _is_rate_limit_error(self, exc: Exception) -> bool:
        """Check if an exception represents a rate limit error.

        Uses proper exception type checking rather than string matching.
        Google's API raises ResourceExhausted (HTTP 429/gRPC 8) for rate limits.
        """
        # Check for Google API rate limit exceptions
        if isinstance(
            exc,
            google_exceptions.ResourceExhausted | google_exceptions.TooManyRequests,
        ):
            return True

        # Fallback: check for 429 status code in the error
        return getattr(exc, "code", None) == 429

    async def _generate_with_model(self, prompt: str, model: str) -> bytes:
        """Generate image with specified model using native async."""
        response = await self._client.aio.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
                image_config=types.ImageConfig(
                    aspect_ratio="1:1",
                ),
            ),
        )

        if response.parts is not None:
            for part in response.parts:
                if part.inline_data and part.inline_data.data is not None:
                    return bytes(part.inline_data.data)

        raise ValueError("Gemini did not return image data")

    async def enhance_prompt(self, context: str, description: str) -> str:
        """Enhance a prompt using Gemini 3 Flash for emoji generation.

        Uses Google's prompting best practices:
        - Clear role definition and task description
        - Structured input/output format
        - Few-shot examples for consistent output
        - Specific constraints and requirements
        """
        # System instruction following Google's best practices:
        # 1. Define the role clearly
        # 2. Provide specific requirements
        # 3. Include examples
        # 4. Specify output format
        system_instruction = """You are an expert prompt engineer specializing in \
creating prompts for AI image generation of Slack emojis.

TASK: Transform the user's context and description into an optimized image \
generation prompt for creating a Slack emoji.

REQUIREMENTS:
- Output must specify a transparent background
- Optimize for 128x128 pixel display (Slack emoji size)
- Use bold shapes and high contrast for small-size readability
- Keep designs simple - avoid fine details that disappear at small sizes

OUTPUT FORMAT:
Return ONLY the optimized prompt text. No explanations, no quotes, no formatting.

STYLE GUIDELINES:
- Cartoon style: playful, bold outlines, vibrant colors
- Minimalist: clean lines, limited colors, professional
- Pixel art: retro gaming aesthetic, blocky shapes
- Realistic: detailed but simplified for emoji scale

EXAMPLES:

Input Context: "Just deployed the new feature!"
Input Description: "rocket ship"
Output: Cartoon rocket ship with bright orange flames launching upward, \
bold black outlines, vibrant blue body with red fins, transparent background, \
optimized for 128x128 pixel Slack emoji

Input Context: "Team standup meeting"
Input Description: "coffee cup"
Output: Steaming coffee mug in minimalist flat design, warm brown with \
white steam curls, simple clean lines, transparent background, \
optimized for 128x128 pixel Slack emoji

Input Context: "Bug fixed!"
Input Description: "celebration"
Output: Colorful party popper with confetti burst, cartoon style with \
bold outlines, bright rainbow confetti pieces, transparent background, \
optimized for 128x128 pixel Slack emoji"""

        user_message = f"""Input Context: {context}
Input Description: {description}
Output:"""

        try:
            response = await self._client.aio.models.generate_content(
                model=self._text_model,
                contents=user_message,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.7,  # Balanced creativity
                    max_output_tokens=256,  # Prompts should be concise
                ),
            )

            if response.text:
                return response.text.strip()

            raise ValueError("Gemini did not return text response")

        except Exception as exc:
            if self._is_rate_limit_error(exc):
                raise RateLimitExceededError(str(exc)) from exc
            raise

    async def _generate_with_imagen(self, prompt: str) -> bytes:
        """Generate image with Imagen 4 Ultra fallback.

        Uses the Imagen API which has a different method signature than Gemini.
        """
        response = await self._client.aio.models.generate_images(
            model=self._fallback_model,  # "imagen-4.0-ultra-generate-001"
            prompt=prompt,
            config=types.GenerateImagesConfig(
                number_of_images=1,
                aspect_ratio="1:1",
            ),
        )

        if response.generated_images:
            first_image = response.generated_images[0]
            if first_image.image and first_image.image.image_bytes is not None:
                return bytes(first_image.image.image_bytes)

        raise ValueError("Imagen did not return image data")

    async def generate_image(
        self,
        prompt: str,
        num_images: int = 1,
        quality: str = "high",  # Unused - for protocol compatibility
        background: str = "transparent",  # Unused - handled via prompt text
    ) -> list[bytes]:
        """Generate images using Gemini with Imagen Ultra fallback.

        Note: Google APIs don't have quality/background parameters. These must be
        specified in the prompt text using get_background_prompt_suffix().

        Args:
            prompt: Text description (should include "transparent background" if needed)
            num_images: Number of images to generate (1-4)
            quality: Unused - for protocol compatibility with OpenAI
            background: Unused - for protocol compatibility with OpenAI

        Returns:
            List of image bytes
        """
        # Unused parameters kept for protocol compatibility
        _ = quality, background
        images = []
        n = min(num_images, 4)

        for _ in range(n):
            try:
                start_time = time.monotonic()
                image_bytes = await self._generate_with_model(prompt, self._model)
                duration_s = time.monotonic() - start_time
                log_event(
                    self._logger,
                    logging.INFO,
                    "Image generated",
                    event="model_generation",
                    provider="google_gemini",
                    model=self._model,
                    is_fallback=False,
                )
                if self._metrics is not None:
                    self._metrics.record_emoji_generated(
                        provider="google_gemini",
                        model=self._model,
                        is_fallback=False,
                        duration_s=duration_s,
                    )
                images.append(image_bytes)
            except Exception as exc:
                if self._is_rate_limit_error(exc):
                    raise RateLimitExceededError(str(exc)) from exc

                self._logger.warning(
                    "%s failed, falling back to %s: %s",
                    self._model,
                    self._fallback_model,
                    exc,
                )
                try:
                    start_time = time.monotonic()
                    image_bytes = await self._generate_with_imagen(prompt)
                    duration_s = time.monotonic() - start_time
                    log_event(
                        self._logger,
                        logging.INFO,
                        "Image generated via Imagen",
                        event="model_generation",
                        provider="google_imagen",
                        model=self._fallback_model,
                        is_fallback=True,
                    )
                    if self._metrics is not None:
                        self._metrics.record_emoji_generated(
                            provider="google_imagen",
                            model=self._fallback_model,
                            is_fallback=True,
                            duration_s=duration_s,
                        )
                    images.append(image_bytes)
                except Exception as fallback_exc:
                    if self._is_rate_limit_error(fallback_exc):
                        raise RateLimitExceededError(
                            str(fallback_exc)
                        ) from fallback_exc
                    raise fallback_exc

        return images
