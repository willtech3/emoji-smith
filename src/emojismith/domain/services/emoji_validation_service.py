"""Domain service for validating and creating emoji entities."""

from emojismith.domain.entities.generated_emoji import GeneratedEmoji
from emojismith.domain.repositories.image_validator import ImageValidator


class EmojiValidationService:
    """Domain service that validates image data and creates emoji entities."""

    def __init__(self, image_validator: ImageValidator) -> None:
        """Initialize the validation service.

        Args:
            image_validator: Protocol implementation for image validation
        """
        self._image_validator = image_validator

    def validate_and_create_emoji(self, image_data: bytes, name: str) -> GeneratedEmoji:
        """Validate image data and create emoji entity.

        This method orchestrates the validation of image format and dimensions
        before creating the GeneratedEmoji entity, maintaining Clean Architecture
        by keeping infrastructure concerns out of the domain entity.

        Args:
            image_data: Raw image bytes to validate
            name: Name for the emoji

        Returns:
            Valid GeneratedEmoji entity

        Raises:
            ValueError: If image data doesn't meet emoji requirements
        """
        # Validate image format and dimensions using injected validator
        self._image_validator.validate_emoji_format(image_data)

        # Create and return the domain entity
        # The entity itself handles basic validation (non-empty data, size limits)
        return GeneratedEmoji(image_data=image_data, name=name)

    def get_image_info(self, image_data: bytes) -> tuple[int, int]:
        """Get image dimensions for informational purposes.

        Args:
            image_data: Raw image bytes to analyze

        Returns:
            Tuple of (width, height) in pixels
        """
        return self._image_validator.get_image_dimensions(image_data)
