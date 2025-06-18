"""Simplified webhook handler for package Lambda deployment."""

import json
import logging
import re
from typing import Dict, Any

from webhook.domain.slack_message import SlackMessage
from shared.domain.entities import EmojiGenerationJob
from shared.domain.value_objects import EmojiSharingPreferences
from webhook.domain.slack_payloads import MessageActionPayload, ModalSubmissionPayload
from webhook.repositories.slack_repository import SlackRepository
from webhook.repositories.job_queue_repository import JobQueueRepository


class WebhookHandler:
    """Handles Slack webhook events with immediate modal opening."""

    def __init__(
        self, slack_repo: SlackRepository, job_queue: JobQueueRepository
    ) -> None:
        self._slack_repo = slack_repo
        self._job_queue = job_queue
        self._logger = logging.getLogger(__name__)

    async def handle_message_action(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle Slack message action - open modal immediately."""
        # Parse payload into structured dataclass first
        try:
            action_payload = MessageActionPayload.from_dict(payload)
        except (KeyError, TypeError) as e:
            self._logger.error(f"Invalid message action payload: {e}")
            raise ValueError("Invalid message action payload") from e

        # Validate callback ID after successful parsing
        if action_payload.callback_id != "create_emoji_reaction":
            raise ValueError("Invalid callback_id")

        # Create domain message object
        slack_message = SlackMessage(
            text=action_payload.message.text,
            user_id=action_payload.message.user,  # Original message author
            channel_id=action_payload.channel.id,
            timestamp=action_payload.message.ts,
            team_id=action_payload.team.id,
        )

        # Extract trigger ID for modal
        trigger_id = action_payload.trigger_id

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
        # Parse payload into structured dataclass
        try:
            modal_payload = ModalSubmissionPayload.from_dict(payload)
        except (KeyError, TypeError) as e:
            self._logger.error(f"Invalid modal submission payload: {e}")
            raise ValueError("Invalid modal submission payload") from e

        # Validate callback ID
        if modal_payload.view.callback_id != "emoji_creation_modal":
            raise ValueError("Invalid callback_id for modal submission")

        # Extract form data with proper error handling
        try:
            state = modal_payload.view.state.values

            # Extract description with None check
            desc_block = state["emoji_description"].description
            if desc_block is None:
                raise ValueError("Missing emoji description")
            description = desc_block.value

            name_block = state["emoji_name"].name
            if name_block is None:
                raise ValueError("Missing emoji name")
            emoji_name = name_block.value

            if not re.fullmatch(r"[a-z0-9_]+", emoji_name):
                raise ValueError(
                    "Emoji name must contain only lowercase letters, "
                    "numbers, and underscores"
                )
            if len(emoji_name) > 32:
                raise ValueError("Emoji name must be 32 characters or less")

            # Extract share location with None check
            share_select = state["share_location"].share_location_select
            if share_select is None:
                raise ValueError("Missing share location")
            share_location = share_select["selected_option"]["value"]

            # Extract visibility with None check
            vis_select = state["instruction_visibility"].visibility_select
            if vis_select is None:
                raise ValueError("Missing visibility setting")
            visibility = vis_select["selected_option"]["value"]

            # Extract image size with None check
            size_select = state["image_size"].size_select
            if size_select is None:
                raise ValueError("Missing image size")
            image_size = size_select["selected_option"]["value"]

            metadata = json.loads(modal_payload.view.private_metadata)
        except (KeyError, json.JSONDecodeError, ValueError) as exc:
            self._logger.exception("Malformed modal submission form data")
            raise ValueError("Malformed modal submission form data") from exc

        # Create emoji generation job with type-safe shared domain models
        sharing_preferences = EmojiSharingPreferences.from_form_values(
            share_location=share_location,
            instruction_visibility=visibility,
            image_size=image_size,
            thread_ts=metadata.get("thread_ts"),
        )

        job = EmojiGenerationJob.create_new(
            user_description=description,
            message_text=metadata["message_text"],
            user_id=metadata["user_id"],
            channel_id=metadata["channel_id"],
            timestamp=metadata["timestamp"],
            team_id=metadata["team_id"],
            sharing_preferences=sharing_preferences,
            thread_ts=metadata.get("thread_ts"),
            emoji_name=emoji_name,
        )

        # Queue job for worker Lambda
        try:
            await self._job_queue.enqueue_job(job)
            self._logger.info(
                "Queued emoji generation job",
                extra={"job_id": job.job_id, "user_id": job.user_id},
            )
            return {"response_action": "clear"}
        except Exception:
            self._logger.exception("Failed to queue emoji generation job")
            return {
                "response_action": "errors",
                "errors": {
                    "emoji_description": (
                        "Failed to queue emoji generation. Please try again."
                    )
                },
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
                        "text": (
                            f'Creating emoji for message: "'
                            f"{slack_message.text[:100]}"
                            f"{'...' if len(slack_message.text) > 100 else ''}\""
                        ),
                    },
                },
                {
                    "type": "input",
                    "block_id": "emoji_name",
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "name",
                        "placeholder": {
                            "type": "plain_text",
                            "text": "e.g., 'coding_wizard' → becomes :coding_wizard:",
                        },
                    },
                    "label": {"type": "plain_text", "text": "Emoji Name"},
                },
                {
                    "type": "input",
                    "block_id": "emoji_description",
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "description",
                        "placeholder": {
                            "type": "plain_text",
                            "text": "e.g., 'A retro computer terminal with green text'",
                        },
                    },
                    "label": {"type": "plain_text", "text": "Emoji Description"},
                },
                {
                    "type": "input",
                    "block_id": "share_location",
                    "element": {
                        "type": "static_select",
                        "action_id": "share_location_select",
                        "placeholder": {
                            "type": "plain_text",
                            "text": "Choose sharing location",
                        },
                        "options": [
                            {
                                "text": {
                                    "type": "plain_text",
                                    "text": "Current channel",
                                },
                                "value": "channel",
                            },
                            {
                                "text": {
                                    "type": "plain_text",
                                    "text": "Direct message",
                                },
                                "value": "dm",
                            },
                        ],
                        "initial_option": {
                            "text": {"type": "plain_text", "text": "Current channel"},
                            "value": "channel",
                        },
                    },
                    "label": {"type": "plain_text", "text": "Share Location"},
                },
                {
                    "type": "input",
                    "block_id": "instruction_visibility",
                    "element": {
                        "type": "static_select",
                        "action_id": "visibility_select",
                        "placeholder": {
                            "type": "plain_text",
                            "text": "Choose instruction visibility",
                        },
                        "options": [
                            {
                                "text": {
                                    "type": "plain_text",
                                    "text": "Show description",
                                },
                                "value": "visible",
                            },
                            {
                                "text": {
                                    "type": "plain_text",
                                    "text": "Hide description",
                                },
                                "value": "hidden",
                            },
                        ],
                        "initial_option": {
                            "text": {"type": "plain_text", "text": "Show description"},
                            "value": "visible",
                        },
                    },
                    "label": {"type": "plain_text", "text": "Instruction Visibility"},
                },
                {
                    "type": "input",
                    "block_id": "image_size",
                    "element": {
                        "type": "static_select",
                        "action_id": "size_select",
                        "placeholder": {
                            "type": "plain_text",
                            "text": "Choose image size",
                        },
                        "options": [
                            {
                                "text": {
                                    "type": "plain_text",
                                    "text": "512x512 (Recommended)",
                                },
                                "value": "512x512",
                            },
                            {
                                "text": {
                                    "type": "plain_text",
                                    "text": "256x256 (Smaller)",
                                },
                                "value": "256x256",
                            },
                            {
                                "text": {
                                    "type": "plain_text",
                                    "text": "1024x1024 (Larger)",
                                },
                                "value": "1024x1024",
                            },
                        ],
                        "initial_option": {
                            "text": {
                                "type": "plain_text",
                                "text": "512x512 (Recommended)",
                            },
                            "value": "512x512",
                        },
                    },
                    "label": {"type": "plain_text", "text": "Image Size"},
                },
            ],
            "submit": {"type": "plain_text", "text": "Generate Emoji"},
            "private_metadata": json.dumps(metadata),
        }

        self._logger.info(
            "Opening emoji creation modal", extra={"trigger_id": trigger_id}
        )
        await self._slack_repo.open_modal(trigger_id=trigger_id, view=modal_view)
