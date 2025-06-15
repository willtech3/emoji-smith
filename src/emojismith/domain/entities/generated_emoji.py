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
    MAX_SIZE: ClassVar[int] = 64 * 1024

    def __post_init__(self) -> None:
        if not self.image_data:
            raise ValueError("image_data is required")
        if not self.name:
            raise ValueError("name is required")
        if len(self.image_data) >= self.MAX_SIZE:
            raise ValueError("emoji must be smaller than 64KB")
