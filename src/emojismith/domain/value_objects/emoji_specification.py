from dataclasses import dataclass

from shared.domain.value_objects import EmojiStylePreferences


@dataclass(frozen=True)
class EmojiSpecification:
    """Value object describing the emoji to generate."""

    description: str
    context: str
    style_preferences: EmojiStylePreferences = EmojiStylePreferences()

    def __post_init__(self) -> None:
        if not self.description:
            raise ValueError("description is required")
        if not self.context:
            raise ValueError("context is required")

    def to_prompt(self) -> str:
        """Combine context and description into a single prompt."""
        base = f"{self.context.strip()} {self.description.strip()}"
        prefs = self.style_preferences
        return (
            f"{base} in {prefs.style_type.value} style with "
            f"{prefs.color_scheme.value} colors "
            f"{prefs.detail_level.value} detail and {prefs.tone.value} tone"
        )
