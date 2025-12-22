"""Image provider value object."""

from enum import Enum


class ImageProvider(str, Enum):
    """Available image generation providers."""

    OPENAI = "openai"
    GOOGLE_GEMINI = "google_gemini"

    @classmethod
    def from_string(cls, value: str) -> "ImageProvider":
        """Create provider from string, defaulting to OpenAI."""
        try:
            return cls(value.lower())
        except ValueError:
            return cls.OPENAI
