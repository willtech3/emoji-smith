"""OpenAI repository protocol for AI operations."""

from typing import Protocol


class OpenAIRepository(Protocol):
    """Protocol for OpenAI operations used in emoji generation."""

    async def optimize_prompt(self, context: str, description: str) -> str:
        """Enhance prompt using o3 with message context and user description."""
        ...

    async def generate_image(self, prompt: str) -> bytes:
        """Generate image bytes using DALL-E from the given prompt."""
        ...
