"""Slack API implementation for webhook package."""

import logging
from typing import Dict, Any
from slack_sdk.web.async_client import AsyncWebClient

from webhook.repositories.slack_repository import SlackRepository


class SlackAPIRepository(SlackRepository):
    """Slack API implementation using slack-sdk."""

    def __init__(self, client: AsyncWebClient) -> None:
        self._client = client
        self._logger = logging.getLogger(__name__)

    async def open_modal(self, trigger_id: str, view: Dict[str, Any]) -> None:
        """Open a modal dialog in Slack."""
        self._logger.info(f"Opening modal with trigger_id: {trigger_id}")
        await self._client.views_open(trigger_id=trigger_id, view=view)
