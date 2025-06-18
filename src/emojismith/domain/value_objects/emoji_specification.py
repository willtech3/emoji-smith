from dataclasses import dataclass, field

from shared.domain.value_objects import EmojiStylePreferences


@dataclass(frozen=True)
class EmojiSpecification:
    """Value object describing the emoji to generate."""

    description: str
    context: str
    style: EmojiStylePreferences = field(default_factory=EmojiStylePreferences)

    def __post_init__(self) -> None:
        if not self.description:
            raise ValueError("description is required")
        if not self.context:
            raise ValueError("context is required")

    def to_prompt(self) -> str:
        """Combine context and description into a single prompt."""
        base = f"{self.context.strip()} {self.description.strip()}"
        if self.style:
            return f"{base} {self.style.to_prompt_fragment()}"
        return base
