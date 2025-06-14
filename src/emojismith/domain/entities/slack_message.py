"""SlackMessage domain entity."""

from dataclasses import dataclass


@dataclass(frozen=True)
class SlackMessage:
    """Domain entity representing a Slack message for emoji generation."""

    text: str
    user_id: str
    channel_id: str
    timestamp: str
    team_id: str

    def __post_init__(self) -> None:
        """Validate required fields and truncate text if needed."""
        if not self.user_id:
            raise ValueError("user_id is required")
        if not self.channel_id:
            raise ValueError("channel_id is required")

        # Truncate text to 1000 characters if longer
        if len(self.text) > 1000:
            object.__setattr__(self, "text", self.text[:1000])

    def get_context_for_ai(self) -> str:
        """Get message context suitable for AI processing."""
        # Truncate to 200 characters for AI context
        context = self.text[:200] if len(self.text) > 200 else self.text
        return context
