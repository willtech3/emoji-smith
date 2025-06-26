"""Configuration-based implementation of StyleTemplateRepository."""

from typing import Optional
from emojismith.domain.repositories.style_template_repository import (
    StyleTemplateRepository,
)
from emojismith.domain.value_objects.style_template import StyleTemplate


class StyleTemplateConfigRepository(StyleTemplateRepository):
    """Repository that provides style templates from configuration."""

    def __init__(self) -> None:
        """Initialize with hardcoded templates."""
        self._templates = {
            "cartoon": StyleTemplate(
                style="cartoon",
                prefix="Cartoon emoji style, rounded shapes, friendly character",
                suffix="bold outlines, vibrant colors, simple background",
                keywords=["cute", "bubbly", "expressive", "animated"],
                avoid=["realistic", "detailed textures", "complex shading"],
            ),
            "pixel_art": StyleTemplate(
                style="pixel_art",
                prefix="8-bit pixel art emoji style, retro game aesthetic",
                suffix="limited color palette, crisp pixels, no anti-aliasing",
                keywords=["blocky", "nostalgic", "arcade", "sprites"],
                avoid=["smooth gradients", "realistic proportions"],
            ),
            "minimalist": StyleTemplate(
                style="minimalist",
                prefix="Minimalist emoji icon, simple geometric shapes",
                suffix="flat design, maximum 3 colors, lots of negative space",
                keywords=["clean", "modern", "essential", "reduced"],
                avoid=["ornate", "detailed", "textured", "busy"],
            ),
            "realistic": StyleTemplate(
                style="realistic",
                prefix="Realistic emoji rendering, detailed but iconic",
                suffix="soft lighting, subtle textures, professional finish",
                keywords=["lifelike", "dimensional", "polished"],
                avoid=["cartoon", "abstract", "pixelated"],
            ),
        }

    def get_template(self, style: str) -> Optional[StyleTemplate]:
        """Retrieve a style template by style name."""
        return self._templates.get(style)

    def get_default_template(self) -> StyleTemplate:
        """Get the default style template (cartoon)."""
        return self._templates["cartoon"]
