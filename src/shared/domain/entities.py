"""Shared domain entities for emoji generation."""

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from shared.domain.value_objects import (
    EmojiSharingPreferences,
    JobStatus,
    EmojiStylePreferences,
)


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
    thread_ts: Optional[str]
    style_preferences: EmojiStylePreferences | None
    created_at: datetime

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
        thread_ts: Optional[str] = None,
        style_preferences: EmojiStylePreferences | None = None,
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
            style_preferences=style_preferences,
            created_at=datetime.now(timezone.utc),
        )

    def to_dict(self) -> Dict[str, Any]:
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
            "thread_ts": self.thread_ts,
            "style_preferences": (
                self.style_preferences.to_dict() if self.style_preferences else None
            ),
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EmojiGenerationJob":
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
            thread_ts=data.get("thread_ts"),
            style_preferences=(
                EmojiStylePreferences.from_dict(data["style_preferences"])
                if data.get("style_preferences")
                else None
            ),
            created_at=datetime.fromisoformat(data["created_at"]),
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
