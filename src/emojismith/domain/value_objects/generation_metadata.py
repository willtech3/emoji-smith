"""Value object for tracking emoji generation metadata."""

from dataclasses import dataclass


@dataclass(frozen=True)
class GenerationMetadata:
    """Tracks metadata about the emoji generation process."""

    used_fallback: bool
    fallback_reason: str | None = None
    quality_score: float | None = None
    quality_issues: list[str] | None = None
    suggestions: list[str] | None = None

    def get_user_notification(self) -> str | None:
        """Get a user-friendly notification message if fallback was used.

        Returns:
            A message to display to users, or None if no notification needed
        """
        if not self.used_fallback:
            return None

        message_parts = []

        if self.fallback_reason:
            message_parts.append(f"💡 {self.fallback_reason}")

        if self.suggestions:
            tips = "Tips for better results: " + ", ".join(self.suggestions)
            message_parts.append(tips)

        return " ".join(message_parts) if message_parts else None
