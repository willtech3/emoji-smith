"""Style template value object for emoji generation."""

from dataclasses import dataclass, field
from typing import List


@dataclass(frozen=True)
class StyleTemplate:
    """Immutable style template for emoji generation."""

    style: str
    prefix: str
    suffix: str
    keywords: List[str] = field(default_factory=list)
    avoid: List[str] = field(default_factory=list)
