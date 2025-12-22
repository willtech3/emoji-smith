"""Image generation repository protocol."""

from typing import Protocol


class ImageGenerationRepository(Protocol):
    """Protocol for image generation providers."""

    async def generate_image(self, prompt: str) -> bytes:
        """Generate an image from the given prompt.

        Args:
            prompt: The text description for image generation.

        Returns:
            Raw image bytes (PNG format).

        Raises:
            RateLimitExceededError: When API rate limit is hit.
            ValueError: When generation fails or returns no data.
        """
        ...
