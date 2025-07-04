"""Manager for style-specific prompt templates."""

from emojismith.domain.repositories.style_template_repository import (
    StyleTemplateRepository,
)
from emojismith.domain.value_objects.style_template import StyleTemplate
from shared.domain.value_objects import StyleType

# Configuration constants
MAX_KEYWORDS_TO_ADD = 2


class StyleTemplateManager:
    """Manages style-specific templates for prompt generation."""

    def __init__(self, template_repository: StyleTemplateRepository) -> None:
        """Initialize with style template repository."""
        self._template_repository = template_repository

    def get_template(self, style_type: StyleType) -> StyleTemplate:
        """Get template for specific style type."""
        return self._template_repository.get_template(style_type)

    def get_all_templates(self) -> dict[StyleType, StyleTemplate]:
        """Get all available templates."""
        return self._template_repository.get_all_templates()

    def apply_style_template(self, base_prompt: str, style_type: StyleType) -> str:
        """Apply style template to enhance base prompt."""
        template = self.get_template(style_type)

        # Handle empty prompt
        if not base_prompt.strip():
            return template.format_prompt("")

        # Remove words that should be avoided for this style
        cleaned_prompt = self._remove_avoid_words(base_prompt, template)

        # Add keywords that aren't already in the prompt
        enhanced_prompt = self._add_missing_keywords(cleaned_prompt, template)

        # Format with template prefix and suffix
        return template.format_prompt(enhanced_prompt)

    def _remove_avoid_words(self, prompt: str, template: StyleTemplate) -> str:
        """Remove words that conflict with the style."""
        words = prompt.split()
        cleaned_words = []

        for word in words:
            # Remove punctuation for comparison but keep original
            word_clean = word.lower().strip('.,!?";:')
            if not template.should_avoid_word(word_clean):
                cleaned_words.append(word)

        return " ".join(cleaned_words)

    def _add_missing_keywords(self, prompt: str, template: StyleTemplate) -> str:
        """Add style keywords that aren't already present."""
        prompt_lower = prompt.lower()

        # Find keywords not already in the original prompt
        missing_keywords = []
        for keyword in template.keywords[:MAX_KEYWORDS_TO_ADD]:
            if keyword.lower() not in prompt_lower:
                missing_keywords.append(keyword)

        # Add keywords naturally
        if missing_keywords:
            keyword_phrase = " and ".join(missing_keywords)
            return f"{keyword_phrase} {prompt}"

        return prompt
