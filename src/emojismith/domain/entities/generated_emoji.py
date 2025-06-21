"""Generated emoji entity."""

from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class GeneratedEmoji:
    """Entity representing a generated emoji image.

    Note: Image format and dimension validation is handled by
    EmojiValidationService using ImageValidator protocol to
    maintain Clean Architecture boundaries.

    Size limits:
    - MAX_SIZE (64KB): Hard limit that triggers validation error
    - RESIZE_THRESHOLD (50KB): Proactive resize suggestion to stay well under limit
    - SLACK_SIZE_LIMIT (128KB): Slack's actual limit (for reference)
    """

    image_data: bytes  # Raw image bytes (not base64 encoded)
    name: str
    format: str = "png"
    MAX_SIZE: ClassVar[int] = 64 * 1024  # Our enforced limit for validation
    SLACK_SIZE_LIMIT: ClassVar[int] = 128 * 1024  # Slack's actual limit
    RESIZE_THRESHOLD: ClassVar[int] = 50 * 1024  # Proactive resize threshold (50KB)

    def __post_init__(self) -> None:
        if not self.image_data:
            raise ValueError("image_data is required")
        if not self.name:
            raise ValueError("name is required")
        if len(self.image_data) >= self.MAX_SIZE:
            raise ValueError("emoji must be smaller than 64KB")
        self.validate_format()

    def needs_resizing(self) -> bool:
        """Check if emoji meets or exceeds our resize threshold."""
        return len(self.image_data) >= self.RESIZE_THRESHOLD

    def validate_format(self) -> None:
        """Validate emoji format is acceptable.

        Raises:
            ValueError: If format is not one of the supported formats.
        """
        if self.format not in ["png", "gif", "jpg"]:
            raise ValueError(
                f"Unsupported format: {self.format}. Must be one of: png, gif, jpg"
            )
