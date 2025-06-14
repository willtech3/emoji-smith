"""Emoji creation service for orchestrating the workflow."""

import json
import logging
from typing import Dict, Any
from emojismith.domain.entities.slack_message import SlackMessage
from emojismith.domain.repositories.slack_repository import SlackRepository


class EmojiCreationService:
    """Service for orchestrating emoji creation workflow."""

    _logger = logging.getLogger(__name__)

    def __init__(self, slack_repo: SlackRepository) -> None:
        self._slack_repo = slack_repo

    async def initiate_emoji_creation(
        self, message: SlackMessage, trigger_id: str
    ) -> None:
        """Initiate emoji creation process by opening modal dialog."""
        # Create modal view with message context
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
                            f"*Message context:*\n> "
                            f"{message.get_context_for_ai()[:100]}..."
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
            "private_metadata": json.dumps(
                {
                    "message_text": message.text,
                    "user_id": message.user_id,
                    "channel_id": message.channel_id,
                    "timestamp": message.timestamp,
                    "team_id": message.team_id,
                }
            ),
        }

        self._logger.info(
            "Opening emoji creation modal", extra={"trigger_id": trigger_id}
        )
        await self._slack_repo.open_modal(trigger_id=trigger_id, view=modal_view)

    async def handle_modal_submission(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle modal submission and queue emoji generation job."""
        # Validate and extract user description and message metadata
        view = payload.get("view", {})
        state = view.get("state", {}).get("values", {})
        try:
            description = state["emoji_description"]["description"]["value"]
            # metadata = json.loads(view.get("private_metadata", "{}"))
        except (KeyError, json.JSONDecodeError) as exc:
            self._logger.exception("Malformed modal submission payload")
            raise ValueError("Malformed modal submission payload") from exc

        self._logger.info(
            "Processing modal submission", extra={"description": description}
        )

        # TODO: Queue job for async processing when background worker is available
        # e.g., await self._queue_emoji_generation_job({
        #     **metadata, "user_description": description
        # })

        return {"response_action": "clear"}

    async def process_emoji_generation_job(self, job_data: Dict[str, Any]) -> None:
        """Process emoji generation job (would be called by background worker)."""
        # TODO: This will be implemented when we add AI integration
        # For now, just a placeholder that could:
        # 1. Generate emoji using AI service
        # 2. Upload emoji to Slack workspace
        # 3. Add reaction to original message
        pass
