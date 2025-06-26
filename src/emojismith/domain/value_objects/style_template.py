"""Style template value object for prompt generation."""

from dataclasses import dataclass, field
from typing import Tuple
from shared.domain.value_objects import StyleType


@dataclass(frozen=True)
class StyleTemplate:
    """Immutable template for style-specific prompt generation."""

    style_type: StyleType
    prefix: str
    suffix: str
    keywords: Tuple[str, ...] = field(default_factory=tuple)
    avoid_words: Tuple[str, ...] = field(default_factory=tuple)

    def format_prompt(self, content: str) -> str:
        """Format prompt with prefix, content, and suffix."""
        return f"{self.prefix} {content} {self.suffix}"

    def has_keyword(self, word: str) -> bool:
        """Check if word is in keywords (case-insensitive)."""
        word_lower = word.lower()
        return any(keyword.lower() == word_lower for keyword in self.keywords)

    def should_avoid_word(self, word: str) -> bool:
        """Check if word should be avoided (case-insensitive)."""
        word_lower = word.lower()
        return any(avoid.lower() == word_lower for avoid in self.avoid_words)
