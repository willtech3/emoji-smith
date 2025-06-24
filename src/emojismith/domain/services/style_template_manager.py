"""Manager for style-specific prompt templates."""

from typing import Dict
from emojismith.domain.value_objects.style_template import StyleTemplate
from shared.domain.value_objects import StyleType


class StyleTemplateManager:
    """Manages style-specific templates for prompt generation."""

    def __init__(self) -> None:
        """Initialize with predefined style templates."""
        self._templates = self._create_templates()

    def _create_templates(self) -> Dict[StyleType, StyleTemplate]:
        """Create all style templates."""
        return {
            StyleType.CARTOON: StyleTemplate(
                style_type=StyleType.CARTOON,
                prefix="Create a vibrant, cartoon-style emoji with",
                suffix=(
                    "in a fun, animated style with bold colors and "
                    "expressive features"
                ),
                keywords=(
                    "vibrant",
                    "playful",
                    "colorful",
                    "animated",
                    "bold",
                    "expressive",
                ),
                avoid_words=(
                    "realistic",
                    "photographic",
                    "detailed",
                    "subtle",
                    "muted",
                ),
            ),
            StyleType.PIXEL_ART: StyleTemplate(
                style_type=StyleType.PIXEL_ART,
                prefix="Design a retro pixel art emoji showing",
                suffix="in 8-bit or 16-bit pixel art style with clean pixelated edges",
                keywords=("8-bit", "16-bit", "pixelated", "retro", "blocky", "crisp"),
                avoid_words=("smooth", "realistic", "gradient", "blended", "soft"),
            ),
            StyleType.MINIMALIST: StyleTemplate(
                style_type=StyleType.MINIMALIST,
                prefix="Create a simple, minimalist emoji depicting",
                suffix=(
                    "using clean lines, minimal details, and essential "
                    "elements only"
                ),
                keywords=(
                    "simple",
                    "clean",
                    "minimal",
                    "essential",
                    "basic",
                    "geometric",
                ),
                avoid_words=("complex", "detailed", "ornate", "busy", "cluttered"),
            ),
            StyleType.REALISTIC: StyleTemplate(
                style_type=StyleType.REALISTIC,
                prefix="Generate a realistic, detailed emoji showing",
                suffix="with photorealistic details and natural textures",
                keywords=(
                    "realistic",
                    "detailed",
                    "photorealistic",
                    "natural",
                    "textured",
                ),
                avoid_words=(
                    "cartoon",
                    "abstract",
                    "simplified",
                    "stylized",
                    "pixelated",
                ),
            ),
        }

    def get_template(self, style_type: StyleType) -> StyleTemplate:
        """Get template for specific style type."""
        return self._templates[style_type]

    def get_all_templates(self) -> Dict[StyleType, StyleTemplate]:
        """Get all available templates."""
        return self._templates.copy()

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
        for keyword in template.keywords[:2]:  # Add up to 2 keywords
            if keyword.lower() not in prompt_lower:
                missing_keywords.append(keyword)

        # Add keywords naturally
        if missing_keywords:
            keyword_phrase = " and ".join(missing_keywords)
            return f"{keyword_phrase} {prompt}"

        return prompt
