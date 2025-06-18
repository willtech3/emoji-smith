from dataclasses import dataclass
from typing import Any, Dict


@dataclass(frozen=True)
class SlackMessage:
    """Immutable Slack message entity shared across packages."""

    text: str
    user_id: str
    channel_id: str
    timestamp: str
    team_id: str

    def __post_init__(self) -> None:
        if not self.user_id:
            raise ValueError("user_id is required")
        if not self.channel_id:
            raise ValueError("channel_id is required")
        if len(self.text) > 1000:
            object.__setattr__(self, "text", self.text[:1000])

    def get_context_for_ai(self) -> str:
        context = self.text[:200] if len(self.text) > 200 else self.text
        return context

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "user_id": self.user_id,
            "channel_id": self.channel_id,
            "timestamp": self.timestamp,
            "team_id": self.team_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SlackMessage":
        return cls(
            text=data["text"],
            user_id=data["user_id"],
            channel_id=data["channel_id"],
            timestamp=data["timestamp"],
            team_id=data["team_id"],
        )
