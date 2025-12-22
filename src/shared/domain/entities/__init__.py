"""Entity classes shared across packages."""

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from shared.domain.value_objects import (
    EmojiSharingPreferences,
    EmojiStylePreferences,
    JobStatus,
)

from .slack_message import SlackMessage


@dataclass
class EmojiGenerationJob:
    """Domain entity representing an emoji generation job."""

    job_id: str
    user_description: str
    message_text: str
    user_id: str
    channel_id: str
    timestamp: str
    team_id: str
    emoji_name: str
    status: JobStatus
    sharing_preferences: EmojiSharingPreferences
    created_at: datetime
    thread_ts: str | None = None
    style_preferences: EmojiStylePreferences = field(
        default_factory=EmojiStylePreferences
    )
    image_provider: str = "openai"  # Default for backward compatibility

    @classmethod
    def create_new(
        cls,
        *,
        user_description: str,
        emoji_name: str,
        message_text: str,
        user_id: str,
        channel_id: str,
        timestamp: str,
        team_id: str,
        sharing_preferences: EmojiSharingPreferences,
        style_preferences: EmojiStylePreferences | None = None,
        thread_ts: str | None = None,
        image_provider: str = "openai",
    ) -> "EmojiGenerationJob":
        """Create a new emoji generation job."""
        return cls(
            job_id=str(uuid.uuid4()),
            user_description=user_description,
            message_text=message_text,
            user_id=user_id,
            channel_id=channel_id,
            timestamp=timestamp,
            team_id=team_id,
            emoji_name=emoji_name,
            status=JobStatus.PENDING,
            sharing_preferences=sharing_preferences,
            thread_ts=thread_ts,
            created_at=datetime.now(UTC),
            style_preferences=style_preferences or EmojiStylePreferences(),
            image_provider=image_provider,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "job_id": self.job_id,
            "user_description": self.user_description,
            "message_text": self.message_text,
            "user_id": self.user_id,
            "channel_id": self.channel_id,
            "timestamp": self.timestamp,
            "team_id": self.team_id,
            "emoji_name": self.emoji_name,
            "status": self.status.value,
            "sharing_preferences": self.sharing_preferences.to_dict(),
            "style_preferences": self.style_preferences.to_dict(),
            "thread_ts": self.thread_ts,
            "created_at": self.created_at.isoformat(),
            "image_provider": self.image_provider,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EmojiGenerationJob":
        """Create from dictionary."""
        return cls(
            job_id=data["job_id"],
            user_description=data["user_description"],
            message_text=data["message_text"],
            user_id=data["user_id"],
            channel_id=data["channel_id"],
            timestamp=data["timestamp"],
            team_id=data["team_id"],
            emoji_name=data["emoji_name"],
            status=JobStatus(data["status"]),
            sharing_preferences=EmojiSharingPreferences.from_dict(
                data["sharing_preferences"]
            ),
            style_preferences=EmojiStylePreferences.from_dict(
                data.get("style_preferences", {})
            ),
            thread_ts=data.get("thread_ts"),
            created_at=datetime.fromisoformat(data["created_at"]),
            image_provider=data.get("image_provider", "openai"),
        )

    def mark_as_processing(self) -> None:
        """Mark job as processing."""
        self.status = JobStatus.PROCESSING

    def mark_as_completed(self) -> None:
        """Mark job as completed."""
        self.status = JobStatus.COMPLETED

    def mark_as_failed(self) -> None:
        """Mark job as failed."""
        self.status = JobStatus.FAILED


__all__ = ["EmojiGenerationJob", "SlackMessage"]
