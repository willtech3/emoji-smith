"""Image validation protocol for domain layer."""

from typing import Protocol


class ImageValidator(Protocol):
    """Protocol for validating image data and format."""

    def validate_emoji_format(self, image_data: bytes) -> None:
        """Validate that image data meets emoji requirements.

        Args:
            image_data: Raw image bytes to validate

        Raises:
            ValueError: If image doesn't meet emoji requirements
        """
        ...

    def get_image_dimensions(self, image_data: bytes) -> tuple[int, int]:
        """Get image width and height.

        Args:
            image_data: Raw image bytes to analyze

        Returns:
            Tuple of (width, height) in pixels

        Raises:
            ValueError: If image data is invalid or corrupted
        """
        ...
