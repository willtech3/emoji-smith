"""Slack repository protocol for domain layer."""  # pragma: no cover

from typing import Dict, Any, Protocol


class SlackRepository(Protocol):
    """Protocol for Slack API operations."""

    async def open_modal(self, trigger_id: str, view: Dict[str, Any]) -> None:
        """Open modal dialog in Slack."""
        ...

    async def upload_emoji(self, name: str, image_data: bytes) -> bool:
        """Upload custom emoji to Slack workspace."""
        ...

    async def add_emoji_reaction(
        self, emoji_name: str, channel_id: str, timestamp: str
    ) -> None:
        """Add emoji reaction to a message."""
        ...
