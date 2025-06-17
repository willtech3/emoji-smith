"""Simplified webhook handler for package Lambda deployment."""

import json
import logging
from typing import Dict, Any
from dataclasses import dataclass

from webhook.domain.slack_message import SlackMessage
from webhook.domain.emoji_generation_job import EmojiGenerationJob
from webhook.repositories.slack_repository import SlackRepository
from webhook.repositories.job_queue_repository import JobQueueRepository


@dataclass
class EmojiSharingPreferences:
    """User preferences for emoji sharing."""
    share_location: str
    instruction_visibility: str
    image_size: str


class WebhookHandler:
    """Handles Slack webhook events with immediate modal opening."""

    def __init__(
        self,
        slack_repo: SlackRepository,
        job_queue: JobQueueRepository
    ) -> None:
        self._slack_repo = slack_repo
        self._job_queue = job_queue
        self._logger = logging.getLogger(__name__)

    async def handle_message_action(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle Slack message action - open modal immediately."""
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

        try:
            # Open modal immediately for fast response
            await self._open_emoji_creation_modal(slack_message, trigger_id)
            return {"status": "ok"}
        except Exception:
            self._logger.exception("Failed to open emoji creation modal")
            return {
                "status": "error",
                "error": "Failed to create emoji. Please try again later.",
            }

    async def handle_modal_submission(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle modal submission and queue emoji generation job."""
        # Validate callback ID
        view = payload.get("view", {})
        if view.get("callback_id") != "emoji_creation_modal":
            raise ValueError("Invalid callback_id for modal submission")

        # Extract form data
        state = view.get("state", {}).get("values", {})
        try:
            description = state["emoji_description"]["description"]["value"]
            share_location = state["share_location"]["share_location_select"][
                "selected_option"
            ]["value"]
            visibility = state["instruction_visibility"]["visibility_select"][
                "selected_option"
            ]["value"]
            image_size = state["image_size"]["size_select"]["selected_option"]["value"]
            metadata = json.loads(view.get("private_metadata", "{}"))
        except (KeyError, json.JSONDecodeError) as exc:
            self._logger.exception("Malformed modal submission payload")
            raise ValueError("Malformed modal submission payload") from exc

        # Create emoji generation job
        sharing_preferences = EmojiSharingPreferences(
            share_location=share_location,
            instruction_visibility=visibility,
            image_size=image_size
        )

        job = EmojiGenerationJob.create_new(
            description=description,
            message_text=metadata["message_text"],
            user_id=metadata["user_id"],
            channel_id=metadata["channel_id"],
            timestamp=metadata["timestamp"],
            team_id=metadata["team_id"],
            sharing_preferences=sharing_preferences,
            thread_ts=metadata.get("thread_ts")
        )

        # Queue job for worker Lambda
        try:
            await self._job_queue.enqueue_job(job)
            self._logger.info(
                "Queued emoji generation job",
                extra={"job_id": job.job_id, "user_id": job.user_id}
            )
            return {"response_action": "clear"}
        except Exception:
            self._logger.exception("Failed to queue emoji generation job")
            return {
                "response_action": "errors",
                "errors": {
                    "emoji_description": "Failed to queue emoji generation. Please try again."
                }
            }

    async def _open_emoji_creation_modal(
        self, slack_message: SlackMessage, trigger_id: str
    ) -> None:
        """Open the emoji creation modal immediately."""
        # Create metadata for modal
        metadata = {
            "message_text": slack_message.text,
            "user_id": slack_message.user_id,
            "channel_id": slack_message.channel_id,
            "timestamp": slack_message.timestamp,
            "team_id": slack_message.team_id,
        }

        # Modal view definition
        modal_view = {
            "type": "modal",
            "callback_id": "emoji_creation_modal",
            "title": {"type": "plain_text", "text": "Create Custom Emoji"},
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"Creating emoji for message: \"{slack_message.text[:100]}{'...' if len(slack_message.text) > 100 else ''}\""
                    }
                },
                {
                    "type": "input",
                    "block_id": "emoji_description",
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "description",
                        "placeholder": {"type": "plain_text", "text": "Describe the emoji you want..."}
                    },
                    "label": {"type": "plain_text", "text": "Emoji Description"}
                },
                {
                    "type": "input",
                    "block_id": "share_location",
                    "element": {
                        "type": "static_select",
                        "action_id": "share_location_select",
                        "placeholder": {"type": "plain_text", "text": "Choose sharing location"},
                        "options": [
                            {"text": {"type": "plain_text", "text": "Current channel"}, "value": "channel"},
                            {"text": {"type": "plain_text", "text": "Direct message"}, "value": "dm"}
                        ],
                        "initial_option": {"text": {"type": "plain_text", "text": "Current channel"}, "value": "channel"}
                    },
                    "label": {"type": "plain_text", "text": "Share Location"}
                },
                {
                    "type": "input",
                    "block_id": "instruction_visibility",
                    "element": {
                        "type": "static_select",
                        "action_id": "visibility_select",
                        "placeholder": {"type": "plain_text", "text": "Choose instruction visibility"},
                        "options": [
                            {"text": {"type": "plain_text", "text": "Show description"}, "value": "visible"},
                            {"text": {"type": "plain_text", "text": "Hide description"}, "value": "hidden"}
                        ],
                        "initial_option": {"text": {"type": "plain_text", "text": "Show description"}, "value": "visible"}
                    },
                    "label": {"type": "plain_text", "text": "Instruction Visibility"}
                },
                {
                    "type": "input",
                    "block_id": "image_size",
                    "element": {
                        "type": "static_select",
                        "action_id": "size_select",
                        "placeholder": {"type": "plain_text", "text": "Choose image size"},
                        "options": [
                            {"text": {"type": "plain_text", "text": "512x512 (Recommended)"}, "value": "512x512"},
                            {"text": {"type": "plain_text", "text": "256x256 (Smaller)"}, "value": "256x256"},
                            {"text": {"type": "plain_text", "text": "1024x1024 (Larger)"}, "value": "1024x1024"}
                        ],
                        "initial_option": {"text": {"type": "plain_text", "text": "512x512 (Recommended)"}, "value": "512x512"}
                    },
                    "label": {"type": "plain_text", "text": "Image Size"}
                }
            ],
            "submit": {"type": "plain_text", "text": "Generate Emoji"},
            "private_metadata": json.dumps(metadata),
        }

        self._logger.info(
            "Opening emoji creation modal", extra={"trigger_id": trigger_id}
        )
        await self._slack_repo.open_modal(trigger_id=trigger_id, view=modal_view)