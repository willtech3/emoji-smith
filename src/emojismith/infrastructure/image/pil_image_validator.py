"""PIL-based implementation of ImageValidator protocol."""

from io import BytesIO
from PIL import Image
from emojismith.domain.repositories.image_validator import ImageValidator


class PILImageValidator(ImageValidator):
    """PIL implementation of image validation for emoji requirements."""

    def validate_emoji_format(self, image_data: bytes) -> None:
        """Validate that image data meets emoji requirements.

        Args:
            image_data: Raw image bytes to validate

        Raises:
            ValueError: If image doesn't meet emoji requirements
        """
        try:
            with Image.open(BytesIO(image_data)) as img:
                # Validate format
                if img.format != "PNG":
                    raise ValueError("emoji must be PNG format")

                # Validate dimensions
                if img.width != 128 or img.height != 128:
                    raise ValueError("emoji must be 128x128 pixels")

        except Exception as e:
            if isinstance(e, ValueError):
                raise
            raise ValueError(f"Invalid image data: {e}") from e

    def get_image_dimensions(self, image_data: bytes) -> tuple[int, int]:
        """Get image width and height.

        Args:
            image_data: Raw image bytes to analyze

        Returns:
            Tuple of (width, height) in pixels

        Raises:
            ValueError: If image data is invalid or corrupted
        """
        try:
            with Image.open(BytesIO(image_data)) as img:
                return (img.width, img.height)
        except Exception as e:
            raise ValueError(f"Cannot read image dimensions: {e}") from e
