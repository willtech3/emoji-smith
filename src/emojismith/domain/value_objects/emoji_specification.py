from dataclasses import dataclass


@dataclass(frozen=True)
class EmojiSpecification:
    """Value object describing the emoji to generate."""

    description: str
    context: str
    style: str = "cartoon"

    def __post_init__(self) -> None:
        if not self.description:
            raise ValueError("description is required")
        if not self.context:
            raise ValueError("context is required")

    def to_prompt(self) -> str:
        """Combine context and description into a single prompt."""
        base = f"{self.context.strip()} {self.description.strip()}"
        if self.style:
            return f"{base} in {self.style} style"
        return base
