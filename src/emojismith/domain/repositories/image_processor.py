"""Image processor protocol for domain layer."""

from typing import Protocol


class ImageProcessor(Protocol):
    """Protocol for image processing implementations."""

    def process(self, image_data: bytes) -> bytes:
        """Process raw image data and return optimized PNG."""
        ...
