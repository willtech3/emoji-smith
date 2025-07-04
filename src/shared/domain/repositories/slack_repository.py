"""Protocol definitions for Slack repository interfaces."""

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class SlackModalRepository(Protocol):
    """Protocol for Slack modal operations following ISP principles."""

    async def open_modal(self, trigger_id: str, view: dict[str, Any]) -> None:
        """Open a modal dialog in Slack.

        Args:
            trigger_id: Slack trigger ID from user interaction
            view: Modal view definition following Slack Block Kit format
        """

    async def update_modal(self, view_id: str, view: dict[str, Any]) -> None:
        """Update an existing modal dialog in Slack.

        Args:
            view_id: ID of the view to update
            view: Updated modal view definition following Slack Block Kit format
        """


@runtime_checkable
class SlackEmojiRepository(Protocol):
    """Protocol for Slack emoji operations following ISP principles."""

    async def upload_emoji(self, name: str, image_data: bytes) -> bool:
        """Upload custom emoji to Slack workspace.

        Returns:
            True if upload successful, False otherwise
        """

    async def add_emoji_reaction(
        self, emoji_name: str, channel_id: str, timestamp: str
    ) -> None: ...


@runtime_checkable
class SlackRepository(SlackModalRepository, SlackEmojiRepository, Protocol):
    """Complete Slack repository interface combining modal and emoji operations."""

    pass
