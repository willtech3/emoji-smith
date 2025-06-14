"""Slack API repository implementation."""

from typing import Dict, Any
from slack_sdk.web.async_client import AsyncWebClient


class SlackAPIRepository:
    """Concrete implementation of SlackRepository using Slack SDK."""

    def __init__(self, slack_client: AsyncWebClient) -> None:
        self._client = slack_client

    async def open_modal(self, trigger_id: str, view: Dict[str, Any]) -> None:
        """Open modal dialog in Slack."""
        await self._client.views_open(trigger_id=trigger_id, view=view)

    async def upload_emoji(self, name: str, image_data: bytes) -> bool:
        """Upload custom emoji to Slack workspace."""
        # Note: admin_emoji_add requires admin privileges
        # In practice, this might need to use emoji.add instead
        response = await self._client.admin_emoji_add(
            name=name, url="", image=image_data
        )
        return response.get("ok", False)

    async def add_emoji_reaction(
        self, emoji_name: str, channel_id: str, timestamp: str
    ) -> None:
        """Add emoji reaction to a message."""
        await self._client.reactions_add(
            name=emoji_name, channel=channel_id, timestamp=timestamp
        )
