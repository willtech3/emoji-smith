"""Generated emoji entity."""

from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class GeneratedEmoji:
    """Entity representing a generated emoji image.

    Note: Image format and dimension validation is handled by
    EmojiValidationService using ImageValidator protocol to
    maintain Clean Architecture boundaries.
    """

    image_data: bytes
    name: str
    format: str = "png"
    MAX_SIZE: ClassVar[int] = 64 * 1024
    SLACK_SIZE_LIMIT: ClassVar[int] = 128 * 1024  # Slack's actual limit
    RESIZE_THRESHOLD: ClassVar[int] = 50 * 1024  # Resize if over 50KB to stay safe

    def __post_init__(self) -> None:
        if not self.image_data:
            raise ValueError("image_data is required")
        if not self.name:
            raise ValueError("name is required")
        if len(self.image_data) >= self.MAX_SIZE:
            raise ValueError("emoji must be smaller than 64KB")

    def needs_resizing(self) -> bool:
        """Check if emoji exceeds Slack size limits."""
        return len(self.image_data) > self.RESIZE_THRESHOLD

    def validate_format(self) -> bool:
        """Validate emoji format is acceptable."""
        return self.format in ["png", "gif", "jpg"]
