"""Slack webhook handler for message actions."""

from typing import Dict, Any
from emojismith.domain.entities.slack_message import SlackMessage
from emojismith.application.services.emoji_service import EmojiCreationService


class SlackWebhookHandler:
    """Handles Slack webhook events for emoji creation."""

    def __init__(self, emoji_service: EmojiCreationService) -> None:
        self._emoji_service = emoji_service

    async def handle_message_action(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle Slack message action webhook payload."""
        # Validate callback ID
        if payload.get("callback_id") != "create_emoji_reaction":
            raise ValueError("Invalid callback_id")

        # Extract message details
        message_data = payload["message"]
        slack_message = SlackMessage(
            text=message_data["text"],
            user_id=message_data["user"],  # Original message author
            channel_id=payload["channel"]["id"],
            timestamp=message_data["ts"],
            team_id=payload["team"]["id"],
        )

        # Extract trigger ID for modal
        trigger_id = payload["trigger_id"]

        # Initiate emoji creation process
        await self._emoji_service.initiate_emoji_creation(slack_message, trigger_id)

        return {"status": "ok"}

    async def handle_modal_submission(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle modal submission for emoji creation."""
        # Validate callback ID
        view = payload.get("view", {})
        if view.get("callback_id") != "emoji_creation_modal":
            raise ValueError("Invalid callback_id for modal submission")

        # Delegate to emoji service
        return await self._emoji_service.handle_modal_submission(payload)
