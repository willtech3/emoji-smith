"""Shared value objects for emoji generation domain."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, Any


class ShareLocation(Enum):
    """Where to share the generated emoji."""

    ORIGINAL_CHANNEL = "channel"
    DIRECT_MESSAGE = "dm"
    NEW_THREAD = "new_thread"
    THREAD = "thread"

    @classmethod
    def from_form_value(cls, form_value: str) -> "ShareLocation":
        """Create from Slack form value."""
        mapping = {
            "channel": cls.ORIGINAL_CHANNEL,
            "dm": cls.DIRECT_MESSAGE,
            "new_thread": cls.NEW_THREAD,
            "thread": cls.THREAD,
        }
        return mapping.get(form_value, cls.ORIGINAL_CHANNEL)


class InstructionVisibility(Enum):
    """Visibility of emoji creation instructions."""

    EVERYONE = "EVERYONE"
    SUBMITTER_ONLY = "SUBMITTER_ONLY"

    @classmethod
    def from_form_value(cls, form_value: str) -> "InstructionVisibility":
        """Create from Slack form value."""
        mapping = {
            "visible": cls.EVERYONE,
            "hidden": cls.SUBMITTER_ONLY,
        }
        return mapping.get(form_value, cls.EVERYONE)


class ImageSize(Enum):
    """Image size for emoji generation."""

    EMOJI_SIZE = "EMOJI_SIZE"  # 512x512 - recommended
    SMALL = "SMALL"  # 256x256
    LARGE = "LARGE"  # 1024x1024

    @classmethod
    def from_form_value(cls, form_value: str) -> "ImageSize":
        """Create from Slack form value."""
        mapping = {
            "512x512": cls.EMOJI_SIZE,
            "256x256": cls.SMALL,
            "1024x1024": cls.LARGE,
        }
        return mapping.get(form_value, cls.EMOJI_SIZE)


class JobStatus(Enum):
    """Status of emoji generation job."""

    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class EmojiSharingPreferences:
    """User preferences for emoji sharing and visibility."""

    share_location: ShareLocation
    instruction_visibility: InstructionVisibility
    image_size: ImageSize
    include_upload_instructions: bool = True
    thread_ts: Optional[str] = None

    @classmethod
    def from_form_values(
        cls,
        share_location: str,
        instruction_visibility: str,
        image_size: str,
        thread_ts: Optional[str] = None,
    ) -> "EmojiSharingPreferences":
        """Create from Slack form values."""
        return cls(
            share_location=ShareLocation.from_form_value(share_location),
            instruction_visibility=InstructionVisibility.from_form_value(
                instruction_visibility
            ),
            image_size=ImageSize.from_form_value(image_size),
            thread_ts=thread_ts,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "share_location": self.share_location.value,
            "instruction_visibility": self.instruction_visibility.value,
            "image_size": self.image_size.value,
            "include_upload_instructions": self.include_upload_instructions,
            "thread_ts": self.thread_ts,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EmojiSharingPreferences":
        """Create from dictionary."""
        return cls(
            share_location=ShareLocation(data["share_location"]),
            instruction_visibility=InstructionVisibility(
                data["instruction_visibility"]
            ),
            image_size=ImageSize(data["image_size"]),
            include_upload_instructions=data.get("include_upload_instructions", True),
            thread_ts=data.get("thread_ts"),
        )

    @classmethod
    def default_for_context(
        cls,
        context: str = "general",
        is_in_thread: bool = False,
        thread_ts: Optional[str] = None,
    ) -> "EmojiSharingPreferences":
        """Create default preferences for a given context."""
        return cls(
            share_location=(
                ShareLocation.THREAD if is_in_thread else ShareLocation.ORIGINAL_CHANNEL
            ),
            instruction_visibility=InstructionVisibility.EVERYONE,
            image_size=ImageSize.EMOJI_SIZE,
            include_upload_instructions=True,
            thread_ts=thread_ts,
        )
