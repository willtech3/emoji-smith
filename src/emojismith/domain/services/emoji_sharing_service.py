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


@dataclass(frozen=True)
class EmojiSharingContext:
    """Context for determining sharing strategy."""

    emoji: GeneratedEmoji
    original_message: SlackMessage
    preferences: EmojiSharingPreferences
    workspace_type: WorkspaceType


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

    def determine_sharing_strategy(self, context: EmojiSharingContext) -> None:
        """Determine the best sharing strategy based on workspace capabilities.

        Note: This method is currently not used as the sharing logic is
        implemented directly in the application layer. It's kept for potential
        future use if we decide to reintroduce the strategy pattern.
        """
        # The actual sharing logic is implemented in EmojiCreationService
        # based on the workspace type
        pass
