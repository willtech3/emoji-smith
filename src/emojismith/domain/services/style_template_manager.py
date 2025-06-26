"""Domain service for managing style templates."""

from emojismith.domain.repositories.style_template_repository import (
    StyleTemplateRepository,
)


MAX_KEYWORDS_TO_ADD = 2
MAX_PROMPT_LENGTH = 1000


class StyleTemplateManager:
    """Manage and apply style templates to prompts."""

    def __init__(self, repository: StyleTemplateRepository) -> None:
        """Initialize with a style template repository."""
        self._repository = repository

    def apply_style_template(self, base_prompt: str, style: str) -> str:
        """Apply style template to base prompt.

        Args:
            base_prompt: The base prompt to enhance
            style: The style name to apply

        Returns:
            Enhanced prompt with style-specific modifications
        """
        template = self._repository.get_template(style)
        if not template:
            template = self._repository.get_default_template()

        # Add prefix
        prompt = f"{template.prefix}, {base_prompt}"

        # Add relevant keywords
        prompt_lower = prompt.lower()
        keywords_to_add = [kw for kw in template.keywords if kw not in prompt_lower][
            :MAX_KEYWORDS_TO_ADD
        ]

        if keywords_to_add:
            prompt += f", {', '.join(keywords_to_add)}"

        # Add suffix
        prompt += f", {template.suffix}"

        # Truncate if too long
        if len(prompt) > MAX_PROMPT_LENGTH:
            prompt = prompt[: MAX_PROMPT_LENGTH - 3] + "..."

        return prompt
