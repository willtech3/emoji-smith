"""EmojiSpecification value object.

Defines the requirements for generated emojis.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class EmojiSpecification:
    """Specification for generating Slack-compatible emojis."""

    context: str
    description: str
    size_px: int = 128
    image_format: str = "PNG"
    max_bytes: int = 64_000

    def __post_init__(self) -> None:
        if self.size_px != 128:
            raise ValueError("Emoji size must be 128x128 pixels")
        if self.image_format.upper() != "PNG":
            raise ValueError("Emoji format must be PNG")
        if self.max_bytes > 64_000:
            raise ValueError("max_bytes must be <= 64KB")
