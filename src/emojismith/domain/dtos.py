"""Data Transfer Objects for emojismith domain."""

from dataclasses import dataclass


@dataclass
class GeneratedEmojiDto:
    """DTO for GeneratedEmoji to decouple infrastructure from domain entities."""

    image_data: bytes
    name: str
    format: str = "png"
