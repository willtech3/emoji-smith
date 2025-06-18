from dataclasses import dataclass

from shared.domain.value_objects import StylePreferences


@dataclass(frozen=True)
class EmojiSpecification:
    """Value object describing the emoji to generate."""

    description: str
    context: str
    style_preferences: StylePreferences

    def __post_init__(self) -> None:
        if not self.description:
            raise ValueError("description is required")
        if not self.context:
            raise ValueError("context is required")

    def to_prompt(self) -> str:
        """Combine context, description and style into a single prompt."""
        base = f"{self.context.strip()} {self.description.strip()}"
        fragment = self.style_preferences.to_prompt_fragment()
        if fragment:
            return f"{base} {fragment}".strip()
        return base
