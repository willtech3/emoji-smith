"""Domain service for determining emoji sharing strategy."""

from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from emojismith.domain.entities.generated_emoji import GeneratedEmoji
from emojismith.domain.entities.slack_message import SlackMessage
from emojismith.domain.value_objects.emoji_sharing_preferences import (
    EmojiSharingPreferences,
)


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

    def determine_sharing_strategy(
        self, context: EmojiSharingContext
    ) -> SharingStrategy:
        """Determine the best sharing strategy based on workspace capabilities."""
        if context.workspace_type == WorkspaceType.ENTERPRISE_GRID:
            return DirectEmojiUploadStrategy()
        else:
            # Free and Standard workspaces use file sharing fallback
            return FileSharingFallbackStrategy(preferences=context.preferences)

    async def detect_workspace_type(self) -> WorkspaceType:
        """Detect workspace type from available permissions."""
        # This would check API permissions in real implementation
        # For now, we'll default to STANDARD
        return WorkspaceType.STANDARD
