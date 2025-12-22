from dataclasses import dataclass, field

from emojismith.domain.exceptions import ValidationError
from shared.domain.value_objects import EmojiStylePreferences


@dataclass(frozen=True)
class EmojiSpecification:
    """Value object describing the emoji to generate."""

    description: str
    context: str
    style: EmojiStylePreferences = field(default_factory=EmojiStylePreferences)

    def __post_init__(self) -> None:
        if not self.description:
            raise ValidationError("description is required")
        # context is optional - users may trigger emoji creation on messages
        # without text (e.g., image-only messages)

        # Security: Check for path traversal attempts
        suspicious_patterns = ["../", "..\\", "%2e%2e", "..;", "....//"]
        for pattern in suspicious_patterns:
            if pattern in self.description:
                raise ValidationError(
                    "Invalid input: potential path traversal attempt detected"
                )
            if self.context and pattern in self.context:
                raise ValidationError(
                    "Invalid input: potential path traversal attempt detected"
                )

    def to_prompt(self) -> str:
        """Combine context and description into a single prompt."""
        # Handle empty context gracefully
        if self.context and self.context.strip():
            base = f"{self.context.strip()} {self.description.strip()}"
        else:
            base = self.description.strip()
        if self.style:
            return f"{base} {self.style.to_prompt_fragment()}"
        return base
