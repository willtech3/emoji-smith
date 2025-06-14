"""OpenAI repository protocol for AI operations."""

from typing import Protocol


class OpenAIRepository(Protocol):
    """Protocol for OpenAI prompt enhancement and image generation."""

    async def enhance_prompt(self, context: str, description: str) -> str:
        """Enhance a prompt using o3."""
        ...

    async def generate_image(self, prompt: str) -> bytes:
        """Generate an emoji image using DALL-E."""
        ...
