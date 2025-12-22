"""Google Gemini API repository implementation."""

from __future__ import annotations

import logging

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


class GeminiAPIRepository(ImageGenerationRepository, PromptEnhancerRepository):
    """Concrete Gemini repository for image generation and prompt enhancement.

    Uses native async via client.aio for optimal performance.
    Implements both ImageGenerationRepository and PromptEnhancerRepository protocols.
    """

    def __init__(
        self,
        client: genai.Client,
        model: str = "gemini-3-pro-image-preview",
        fallback_model: str = "gemini-2.5-flash-image",
        text_model: str = "gemini-3-flash-preview",
    ) -> None:
        self._client = client
        self._logger = logging.getLogger(__name__)
        self._model = model
        self._fallback_model = fallback_model
        self._text_model = text_model

    def _is_rate_limit_error(self, exc: Exception) -> bool:
        """Check if an exception represents a rate limit error.

        Uses proper exception type checking rather than string matching.
        Google's API raises ResourceExhausted (HTTP 429) for rate limits.
        """
        # Check for Google API rate limit exceptions
        if isinstance(exc, google_exceptions.ResourceExhausted):
            return True
        if isinstance(exc, google_exceptions.TooManyRequests):
            return True

        # Fallback: check for 429 status code in the error
        if hasattr(exc, "code") and getattr(exc, "code", None) == 429:
            return True

        # Check for quota exceeded (different from rate limit but similar handling)
        if isinstance(exc, google_exceptions.GoogleAPICallError):
            if exc.grpc_status_code is not None:
                # RESOURCE_EXHAUSTED = 8 in gRPC
                if exc.grpc_status_code.value[0] == 8:
                    return True

        return False

    async def _generate_with_model(self, prompt: str, model: str) -> bytes:
        """Generate image with specified model using native async."""
        response = await self._client.aio.models.generate_content(
            model=model,
            contents=prompt,  # String is supported (list optional for multi-modal)
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],  # Required for image output
                image_config=types.ImageConfig(
                    aspect_ratio="1:1",  # Square for emoji
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

    async def generate_image(self, prompt: str) -> bytes:
        """Generate image using Gemini with fallback."""
        try:
            return await self._generate_with_model(prompt, self._model)
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
                return await self._generate_with_model(prompt, self._fallback_model)
            except Exception as fallback_exc:
                if self._is_rate_limit_error(fallback_exc):
                    raise RateLimitExceededError(str(fallback_exc)) from fallback_exc
                raise fallback_exc
