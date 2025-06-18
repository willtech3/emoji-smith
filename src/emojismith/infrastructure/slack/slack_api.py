"""Slack API repository implementation."""

import logging
from typing import Dict, Any
from slack_sdk.web.async_client import AsyncWebClient
from slack_sdk.errors import SlackApiError

from shared.domain.repositories.slack_repository import SlackRepository


class SlackAPIRepository(SlackRepository):
    """Concrete implementation of SlackRepository using Slack SDK."""

    def __init__(self, slack_client: AsyncWebClient) -> None:
        self._client = slack_client
        self._logger = logging.getLogger(__name__)

    async def open_modal(self, trigger_id: str, view: Dict[str, Any]) -> None:
        """Open modal dialog in Slack."""
        await self._client.views_open(trigger_id=trigger_id, view=view)

    async def upload_emoji(self, name: str, image_data: bytes) -> bool:
        """Upload custom emoji to Slack workspace."""
        # TODO: Implement proper image hosting service for production
        # For now, use a mock URL to demonstrate the flow
        # In production, this would upload to S3/CDN and return the URL
        mock_image_url = f"https://example.com/emojis/{name}.png"

        try:
            response = await self._client.admin_emoji_add(name=name, url=mock_image_url)
            return bool(response.get("ok", False))
        except SlackApiError as e:
            # Handle common admin permission errors gracefully
            if e.response.get("error") == "not_allowed_token_type":
                self._logger.warning(
                    "Cannot upload emoji: admin.emoji.add requires Enterprise Grid "
                    "organization with admin token. Current workspace uses bot token."
                )
                return False
            elif e.response.get("error") in ["missing_scope", "not_authed"]:
                self._logger.warning(
                    "Cannot upload emoji: insufficient permissions. "
                    f"Error: {e.response.get('error')}"
                )
                return False
            else:
                # Re-raise unexpected errors
                self._logger.error(f"Unexpected Slack API error: {e}")
                raise

    async def add_emoji_reaction(
        self, emoji_name: str, channel_id: str, timestamp: str
    ) -> None:
        """Add emoji reaction to a message."""
        await self._client.reactions_add(
            name=emoji_name, channel=channel_id, timestamp=timestamp
        )
