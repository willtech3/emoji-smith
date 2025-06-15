"""EmojiGenerationJob domain entity."""

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Any, Optional

from emojismith.domain.value_objects.emoji_sharing_preferences import (
    EmojiSharingPreferences,
    ShareLocation,
    InstructionVisibility,
    ImageSize,
)


class JobStatus(Enum):
    """Enum for job status values."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class EmojiGenerationJob:
    """Domain entity representing an emoji generation job."""

    job_id: str
    message_text: str
    user_description: str
    user_id: str
    channel_id: str
    timestamp: str
    team_id: str
    status: JobStatus
    created_at: datetime
    sharing_preferences: Optional[EmojiSharingPreferences] = None

    @classmethod
    def create_new(
        cls,
        message_text: str,
        user_description: str,
        user_id: str,
        channel_id: str,
        timestamp: str,
        team_id: str,
        sharing_preferences: Optional[EmojiSharingPreferences] = None,
        thread_ts: Optional[str] = None,
    ) -> "EmojiGenerationJob":
        """Create a new emoji generation job with generated ID."""
        # If no preferences provided, create defaults based on context
        if sharing_preferences is None:
            is_in_thread = bool(thread_ts)
            sharing_preferences = EmojiSharingPreferences.default_for_context(
                is_in_thread=is_in_thread,
                thread_ts=thread_ts,
            )

        return cls(
            job_id=str(uuid.uuid4()),
            message_text=message_text,
            user_description=user_description,
            user_id=user_id,
            channel_id=channel_id,
            timestamp=timestamp,
            team_id=team_id,
            status=JobStatus.PENDING,
            created_at=datetime.now(timezone.utc),
            sharing_preferences=sharing_preferences,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert job to dictionary for serialization."""
        result: Dict[str, Any] = {
            "job_id": self.job_id,
            "message_text": self.message_text,
            "user_description": self.user_description,
            "user_id": self.user_id,
            "channel_id": self.channel_id,
            "timestamp": self.timestamp,
            "team_id": self.team_id,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
        }

        if self.sharing_preferences:
            result["sharing_preferences"] = {
                "share_location": self.sharing_preferences.share_location.value,
                "instruction_visibility": (
                    self.sharing_preferences.instruction_visibility.value
                ),
                "include_upload_instructions": (
                    self.sharing_preferences.include_upload_instructions
                ),
                "image_size": self.sharing_preferences.image_size.value,
                "thread_ts": self.sharing_preferences.thread_ts,
            }

        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EmojiGenerationJob":
        """Create job from dictionary."""
        sharing_preferences = None
        if "sharing_preferences" in data and data["sharing_preferences"]:
            prefs_data = data["sharing_preferences"]
            sharing_preferences = EmojiSharingPreferences(
                share_location=ShareLocation(prefs_data["share_location"]),
                instruction_visibility=InstructionVisibility(
                    prefs_data["instruction_visibility"]
                ),
                include_upload_instructions=prefs_data.get(
                    "include_upload_instructions", True
                ),
                image_size=ImageSize(
                    prefs_data.get("image_size", ImageSize.EMOJI_SIZE.value)
                ),
                thread_ts=prefs_data.get("thread_ts"),
            )

        return cls(
            job_id=data["job_id"],
            message_text=data["message_text"],
            user_description=data["user_description"],
            user_id=data["user_id"],
            channel_id=data["channel_id"],
            timestamp=data["timestamp"],
            team_id=data["team_id"],
            status=JobStatus(data["status"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            sharing_preferences=sharing_preferences,
        )

    def mark_processing(self) -> None:
        """Mark job as currently being processed."""
        self.status = JobStatus.PROCESSING

    def mark_completed(self) -> None:
        """Mark job as completed successfully."""
        self.status = JobStatus.COMPLETED

    def mark_failed(self) -> None:
        """Mark job as failed."""
        self.status = JobStatus.FAILED

    def is_processing(self) -> bool:
        """Check if job is currently being processed."""
        return self.status == JobStatus.PROCESSING

    def is_completed(self) -> bool:
        """Check if job is completed."""
        return self.status == JobStatus.COMPLETED

    def is_failed(self) -> bool:
        """Check if job has failed."""
        return self.status == JobStatus.FAILED
