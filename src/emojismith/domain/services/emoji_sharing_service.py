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
        """Detect workspace type from available permissions.

        If detection fails (e.g. missing scopes or API error), we log a warning and
        gracefully fall back to a `STANDARD` workspace assumption so that the
        application continues using the file-sharing strategy instead of
        crashing.
        """
        try:
            # TODO: Implement real permission introspection once method is chosen.
            # For now we pessimise to ENTERPRISE_GRID only if an explicit env var is set.
            import os

            if os.getenv("EMOJISMITH_FORCE_ENTERPRISE", "false").lower() == "true":
                return WorkspaceType.ENTERPRISE_GRID
            return WorkspaceType.STANDARD
        except Exception as exc:  # pragma: no cover – defensive safety net
            import logging

            logging.getLogger(__name__).warning(
                "Unable to auto-detect workspace type – defaulting to STANDARD: %s",
                exc,
            )
            return WorkspaceType.STANDARD
