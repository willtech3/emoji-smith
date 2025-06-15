"""Value object for emoji sharing preferences."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class ShareLocation(str, Enum):
    """Where to share the generated emoji."""

    ORIGINAL_CHANNEL = "original_channel"
    THREAD = "thread"  # Existing thread
    NEW_THREAD = "new_thread"  # Create new thread
    DM = "dm"


class InstructionVisibility(str, Enum):
    """Who should see the upload instructions."""

    EVERYONE = "everyone"
    REQUESTER_ONLY = "requester_only"


class ImageSize(str, Enum):
    """Size of shared image."""

    EMOJI_SIZE = "emoji_size"  # Standard 128x128
    FULL_SIZE = "full_size"  # Original generated size


@dataclass(frozen=True)
class EmojiSharingPreferences:
    """User preferences for how to share generated emojis."""

    share_location: ShareLocation
    instruction_visibility: InstructionVisibility
    include_upload_instructions: bool = True
    image_size: ImageSize = ImageSize.EMOJI_SIZE
    thread_ts: Optional[str] = None

    def __post_init__(self) -> None:
        """Validate preferences after initialization."""
        if self.share_location == ShareLocation.THREAD and not self.thread_ts:
            raise ValueError("Thread timestamp required for thread sharing")

    @classmethod
    def default_for_context(
        cls, is_in_thread: bool, thread_ts: Optional[str] = None
    ) -> "EmojiSharingPreferences":
        """Create default preferences based on message context."""
        if is_in_thread and thread_ts:
            # If requested from a thread, share in that thread
            return cls(
                share_location=ShareLocation.THREAD,
                instruction_visibility=InstructionVisibility.EVERYONE,
                thread_ts=thread_ts,
            )
        else:
            # If requested from channel, create a new thread
            return cls(
                share_location=ShareLocation.NEW_THREAD,
                instruction_visibility=InstructionVisibility.EVERYONE,
            )
