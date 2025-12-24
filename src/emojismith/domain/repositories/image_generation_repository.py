"""Image generation repository protocol."""

from typing import Protocol


class ImageGenerationRepository(Protocol):
    """Protocol for image generation providers."""

    async def generate_image(
        self,
        prompt: str,
        num_images: int = 1,
        quality: str = "high",
        background: str = "transparent",
    ) -> list[bytes]:
        """Generate images from the given prompt.

        Args:
            prompt: The text description for image generation.
            num_images: Number of images to generate (default: 1, max: 4)
            quality: Rendering quality - "auto", "high", "medium", "low"
            background: Background type - "transparent", "opaque", "auto"

        Returns:
            List of raw image bytes (PNG format).

        Raises:
            RateLimitExceededError: When API rate limit is hit.
            ValueError: When generation fails or returns no data.
        """
        ...
