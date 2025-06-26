"""Repository protocol for style templates."""

from typing import Protocol, Optional
from emojismith.domain.value_objects.style_template import StyleTemplate


class StyleTemplateRepository(Protocol):
    """Protocol for accessing style templates."""

    def get_template(self, style: str) -> Optional[StyleTemplate]:
        """Retrieve a style template by style name."""
        ...

    def get_default_template(self) -> StyleTemplate:
        """Get the default style template."""
        ...
