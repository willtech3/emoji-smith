"""Slack message domain model for webhook package."""

from dataclasses import dataclass


@dataclass
class SlackMessage:
    """Represents a Slack message for emoji creation."""

    text: str
    user_id: str
    channel_id: str
    timestamp: str
    team_id: str

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "text": self.text,
            "user_id": self.user_id,
            "channel_id": self.channel_id,
            "timestamp": self.timestamp,
            "team_id": self.team_id,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SlackMessage":
        """Create from dictionary."""
        return cls(
            text=data["text"],
            user_id=data["user_id"],
            channel_id=data["channel_id"],
            timestamp=data["timestamp"],
            team_id=data["team_id"],
        )
