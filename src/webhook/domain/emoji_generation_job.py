"""Emoji generation job domain model for webhook package."""

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional


@dataclass
class EmojiSharingPreferences:
    """User preferences for emoji sharing."""
    share_location: str
    instruction_visibility: str
    image_size: str

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "share_location": self.share_location,
            "instruction_visibility": self.instruction_visibility,
            "image_size": self.image_size,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "EmojiSharingPreferences":
        """Create from dictionary."""
        return cls(
            share_location=data["share_location"],
            instruction_visibility=data["instruction_visibility"],
            image_size=data["image_size"],
        )


@dataclass
class EmojiGenerationJob:
    """Represents an emoji generation job to be processed by worker Lambda."""
    
    job_id: str
    description: str
    message_text: str
    user_id: str
    channel_id: str
    timestamp: str
    team_id: str
    sharing_preferences: EmojiSharingPreferences
    thread_ts: Optional[str]
    created_at: datetime

    @classmethod
    def create_new(
        cls,
        description: str,
        message_text: str,
        user_id: str,
        channel_id: str,
        timestamp: str,
        team_id: str,
        sharing_preferences: EmojiSharingPreferences,
        thread_ts: Optional[str] = None
    ) -> "EmojiGenerationJob":
        """Create a new emoji generation job."""
        return cls(
            job_id=str(uuid.uuid4()),
            description=description,
            message_text=message_text,
            user_id=user_id,
            channel_id=channel_id,
            timestamp=timestamp,
            team_id=team_id,
            sharing_preferences=sharing_preferences,
            thread_ts=thread_ts,
            created_at=datetime.now(timezone.utc)
        )

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "job_id": self.job_id,
            "description": self.description,
            "message_text": self.message_text,
            "user_id": self.user_id,
            "channel_id": self.channel_id,
            "timestamp": self.timestamp,
            "team_id": self.team_id,
            "sharing_preferences": self.sharing_preferences.to_dict(),
            "thread_ts": self.thread_ts,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "EmojiGenerationJob":
        """Create from dictionary."""
        return cls(
            job_id=data["job_id"],
            description=data["description"],
            message_text=data["message_text"],
            user_id=data["user_id"],
            channel_id=data["channel_id"],
            timestamp=data["timestamp"],
            team_id=data["team_id"],
            sharing_preferences=EmojiSharingPreferences.from_dict(data["sharing_preferences"]),
            thread_ts=data.get("thread_ts"),
            created_at=datetime.fromisoformat(data["created_at"]),
        )