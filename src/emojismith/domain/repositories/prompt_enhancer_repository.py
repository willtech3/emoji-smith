"""Protocol for AI-based prompt enhancement.

This protocol abstracts the prompt enhancement functionality,
allowing different AI providers (OpenAI, Google Gemini, etc.)
to implement their own enhancement strategies.
"""

from typing import Protocol


class PromptEnhancerRepository(Protocol):
    """Protocol for AI-based prompt enhancement.

    This enables provider-agnostic prompt enhancement,
    allowing the application layer to use whichever
    AI provider is configured for the request.
    """

    async def enhance_prompt(self, context: str, description: str) -> str:
        """Enhance a prompt using the configured AI model.

        Args:
            context: The context in which the emoji is being created
                (e.g., the Slack message text)
            description: The base description/prompt to enhance

        Returns:
            An enhanced prompt optimized for emoji image generation
        """
        ...
