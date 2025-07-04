"""Configuration-based implementation of style template repository."""

from typing import Dict

# Repository interface is implemented implicitly via duck typing
from emojismith.domain.value_objects.style_template import StyleTemplate
from shared.domain.value_objects import StyleType


class StyleTemplateConfigRepository:
    """Repository that provides style templates from configuration."""

    def __init__(self) -> None:
        """Initialize with default style templates."""
        self._templates = self._load_templates()

    def _load_templates(self) -> Dict[StyleType, StyleTemplate]:
        """Load style templates from configuration."""
        # In a real implementation, this would load from a config file or database
        # For now, we'll keep the templates here but they're properly abstracted
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
                    "using clean lines, minimal details, and essential " "elements only"
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
