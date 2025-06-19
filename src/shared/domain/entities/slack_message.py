"""SlackMessage domain entity shared between packages."""

from dataclasses import dataclass
from typing import Dict, Any


@dataclass(frozen=True)
class SlackMessage:
    """Immutable representation of a Slack message."""

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

        if len(self.text) > 1000:
            object.__setattr__(self, "text", self.text[:1000])

    def get_context_for_ai(self) -> str:
        """Return message context truncated for AI prompts."""
        return self.text[:200] if len(self.text) > 200 else self.text

    def to_dict(self) -> Dict[str, Any]:
        """Serialize message for transport between services."""
        return {
            "text": self.text,
            "user_id": self.user_id,
            "channel_id": self.channel_id,
            "timestamp": self.timestamp,
            "team_id": self.team_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SlackMessage":
        """Create SlackMessage from dictionary."""
        return cls(
            text=data["text"],
            user_id=data["user_id"],
            channel_id=data["channel_id"],
            timestamp=data["timestamp"],
            team_id=data["team_id"],
        )
