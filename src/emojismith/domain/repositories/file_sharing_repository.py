"""Protocol for file sharing repository."""

from dataclasses import dataclass
from typing import Protocol

from emojismith.domain.entities.generated_emoji import GeneratedEmoji
from shared.domain.value_objects import EmojiSharingPreferences


@dataclass
class FileSharingResult:
    """Result of file sharing operation."""

    success: bool
    thread_ts: str | None = None
    file_url: str | None = None
    error: str | None = None


class FileSharingRepository(Protocol):
    """Repository for sharing emoji files."""

    async def share_emoji_file(
        self,
        emoji: GeneratedEmoji,
        channel_id: str,
        preferences: EmojiSharingPreferences,
        requester_user_id: str,
        original_message_ts: str | None = None,
    ) -> FileSharingResult:
        """Share emoji as a file with upload instructions.

        Args:
            emoji: The generated emoji to share
            channel_id: The Slack channel ID
            preferences: Sharing preferences including thread and visibility settings
            requester_user_id: ID of the user who requested the emoji
            original_message_ts: Timestamp of the original message (for threading)

        Returns:
            FileSharingResult with success status and metadata
        """
        ...
