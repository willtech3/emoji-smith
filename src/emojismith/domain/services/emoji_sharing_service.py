"""Domain service for determining emoji sharing strategy."""

from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from emojismith.domain.entities.generated_emoji import GeneratedEmoji
from shared.domain.entities.slack_message import SlackMessage
from shared.domain.value_objects import EmojiSharingPreferences


class WorkspaceType(str, Enum):
    """Type of Slack workspace."""

    FREE = "free"
    STANDARD = "standard"
    ENTERPRISE_GRID = "enterprise_grid"


@dataclass(frozen=True)
class EmojiSharingContext:
    """Context for determining sharing strategy."""

    emoji: GeneratedEmoji
    original_message: SlackMessage
    preferences: EmojiSharingPreferences
    workspace_type: WorkspaceType


class SharingStrategy(Protocol):
    """Protocol for emoji sharing strategies."""

    async def share(self, context: EmojiSharingContext) -> None:
        """Share the emoji according to the strategy."""
        ...


@dataclass
class DirectEmojiUploadStrategy:
    """Strategy for direct emoji upload (Enterprise Grid only)."""

    async def share(self, context: EmojiSharingContext) -> None:
        """Upload emoji directly to workspace."""
        # Implementation delegated to infrastructure layer
        pass


@dataclass
class FileSharingFallbackStrategy:
    """Strategy for sharing emoji via file upload with instructions."""

    preferences: EmojiSharingPreferences

    async def share(self, context: EmojiSharingContext) -> None:
        """Share emoji as file with upload instructions."""
        # Implementation delegated to infrastructure layer
        pass


class EmojiSharingService:
    """Domain service that determines appropriate sharing strategy."""

    def __init__(self, workspace_type: WorkspaceType = WorkspaceType.STANDARD) -> None:
        """Initialize with workspace type.

        Args:
            workspace_type: The type of Slack workspace. Defaults to STANDARD.
        """
        self._workspace_type = workspace_type

    def determine_sharing_strategy(
        self, context: EmojiSharingContext
    ) -> SharingStrategy:
        """Determine the best sharing strategy based on workspace capabilities."""
        if context.workspace_type == WorkspaceType.ENTERPRISE_GRID:
            return DirectEmojiUploadStrategy()
        else:
            # Free and Standard workspaces use file sharing fallback
            return FileSharingFallbackStrategy(preferences=context.preferences)
