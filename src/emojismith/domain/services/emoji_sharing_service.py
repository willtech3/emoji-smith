"""Domain service for determining emoji sharing strategy."""

from dataclasses import dataclass
from enum import Enum

from emojismith.domain.entities.generated_emoji import GeneratedEmoji
from shared.domain.entities.slack_message import SlackMessage
from shared.domain.value_objects import EmojiSharingPreferences


class WorkspaceType(str, Enum):
    """Type of Slack workspace."""

    FREE = "free"
    STANDARD = "standard"
    ENTERPRISE_GRID = "enterprise_grid"


class SharingStrategy(str, Enum):
    """Strategy for sharing a custom emoji."""

    DIRECT_UPLOAD = "direct_upload"
    FILE_SHARE = "file_share"


@dataclass(frozen=True)
class EmojiSharingContext:
    """Context for determining sharing strategy."""

    emoji: GeneratedEmoji
    original_message: SlackMessage
    preferences: EmojiSharingPreferences


class EmojiSharingService:
    """Domain service that determines appropriate sharing strategy."""

    def __init__(self, workspace_type: WorkspaceType = WorkspaceType.STANDARD) -> None:
        """Initialize with workspace type.

        Args:
            workspace_type: The type of Slack workspace. Defaults to STANDARD.
        """
        self._workspace_type = workspace_type

    @property
    def workspace_type(self) -> WorkspaceType:
        """Get the workspace type.

        Returns:
            The type of Slack workspace.
        """
        return self._workspace_type

    def determine_sharing_strategy(
        self, context: EmojiSharingContext
    ) -> SharingStrategy:
        """Determine the best sharing strategy based on workspace capabilities.

        Args:
            context: The emoji sharing context.

        Returns:
            The determined SharingStrategy.
        """
        if self._workspace_type == WorkspaceType.ENTERPRISE_GRID:
            return SharingStrategy.DIRECT_UPLOAD
        return SharingStrategy.FILE_SHARE
