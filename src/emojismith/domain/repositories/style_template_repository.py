"""Protocol for style template repository."""

from typing import Protocol

from emojismith.domain.value_objects.style_template import StyleTemplate
from shared.domain.value_objects import StyleType


class StyleTemplateRepository(Protocol):
    """Repository protocol for accessing style templates."""

    def get_template(self, style_type: StyleType) -> StyleTemplate:
        """Get template for specific style type."""
        ...

    def get_all_templates(self) -> dict[StyleType, StyleTemplate]:
        """Get all available templates."""
        ...
