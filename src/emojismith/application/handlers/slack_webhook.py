"""Slack webhook handler for message actions."""

from typing import Dict, Any, Protocol
from emojismith.domain.entities.slack_message import SlackMessage
from emojismith.domain.repositories import SlackRepository


class EmojiService(Protocol):
    """Protocol for emoji creation service."""

    async def initiate_emoji_creation(
        self, message: SlackMessage, trigger_id: str
    ) -> None:
        """Initiate emoji creation process."""
        ...


class SlackWebhookHandler:
    """Handles Slack webhook events for emoji creation."""

    def __init__(
        self, emoji_service: EmojiService, slack_repo: SlackRepository
    ) -> None:
        self._emoji_service = emoji_service
        self._slack_repo = slack_repo

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

    async def open_emoji_creation_modal(
        self, trigger_id: str, message_context: str
    ) -> None:
        """Open modal dialog for emoji description input."""
        modal_view = {
            "type": "modal",
            "callback_id": "emoji_creation_modal",
            "title": {"type": "plain_text", "text": "Create Emoji Reaction"},
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": (
                            f"*Message context:*\n> " f"{message_context[:100]}..."
                        ),
                    },
                },
                {
                    "type": "input",
                    "block_id": "emoji_description",
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "description",
                        "placeholder": {
                            "type": "plain_text",
                            "text": (
                                "Describe the emoji you want "
                                "(e.g., facepalm reaction)"
                            ),
                        },
                        "multiline": False,
                    },
                    "label": {
                        "type": "plain_text",
                        "text": "Emoji Description",
                    },
                },
            ],
            "submit": {"type": "plain_text", "text": "Generate Emoji"},
        }

        await self._slack_repo.open_modal(trigger_id=trigger_id, view=modal_view)
