"""Protocol for image generator factory."""

from typing import Protocol

from emojismith.domain.repositories.image_generation_repository import (
    ImageGenerationRepository,
)
from emojismith.domain.value_objects.image_provider import ImageProvider


class ImageGeneratorFactory(Protocol):
    """Protocol for creating image generation repositories."""

    def create(self, provider: ImageProvider) -> ImageGenerationRepository:
        """Create an image generator for the specified provider.

        Args:
            provider: The image generation provider to use.

        Returns:
            An image generation repository instance.

        Raises:
            ValueError: If the provider is not supported or configured.
        """
        ...
