"""Simplified webhook handler for package Lambda deployment."""

import json
import logging
import re
from typing import Any

from shared.domain.entities import EmojiGenerationJob
from shared.domain.entities.slack_message import SlackMessage
from shared.domain.repositories import JobQueueProducer, SlackModalRepository
from shared.domain.value_objects import (
    EmojiSharingPreferences,
    EmojiStylePreferences,
)
from webhook.domain.slack_payloads import MessageActionPayload, ModalSubmissionPayload


class WebhookHandler:
    """Handles Slack webhook events with immediate modal opening."""

    def __init__(
        self, slack_repo: SlackModalRepository, job_queue: JobQueueProducer
    ) -> None:
        self._slack_repo = slack_repo
        self._job_queue = job_queue
        self._logger = logging.getLogger(__name__)

    async def handle_message_action(self, payload: dict[str, Any]) -> dict[str, Any]:
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

    async def handle_modal_submission(self, payload: dict[str, Any]) -> dict[str, Any]:
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

            # Extract style preferences from combined block (always present)
            style_prefs = state["style_preferences"]

            style_block = style_prefs.style_select
            if style_block is None:
                raise ValueError("Missing style type")
            style_type = style_block["selected_option"]["value"]

            detail_block = style_prefs.detail_select
            if detail_block is None:
                raise ValueError("Missing detail level")
            detail_level = detail_block["selected_option"]["value"]

            # Extract advanced fields with defaults (may not be present)
            # Share location
            share_select = state["share_location"].share_location_select
            share_location = (
                share_select["selected_option"]["value"] if share_select else "channel"
            )

            # Visibility
            vis_select = state["instruction_visibility"].visibility_select
            visibility = (
                vis_select["selected_option"]["value"] if vis_select else "show"
            )

            # Image size
            size_select = state["image_size"].size_select
            image_size = (
                size_select["selected_option"]["value"] if size_select else "512"
            )

            # Color scheme
            color_block = state["color_scheme"].color_select
            color_scheme = (
                color_block["selected_option"]["value"] if color_block else "auto"
            )

            # Tone
            tone_block = state["tone"].tone_select
            tone = tone_block["selected_option"]["value"] if tone_block else "fun"

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
            style_preferences=EmojiStylePreferences.from_form_values(
                style_type=style_type,
                color_scheme=color_scheme,
                detail_level=detail_level,
                tone=tone,
            ),
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

    def _get_advanced_option_blocks(self) -> list[dict[str, Any]]:
        """Return the advanced option blocks for the modal."""
        return [
            {"type": "divider"},
            {
                "type": "input",
                "block_id": "color_scheme",
                "element": {
                    "type": "static_select",
                    "action_id": "color_select",
                    "initial_option": {
                        "text": {"type": "plain_text", "text": "Auto"},
                        "value": "auto",
                    },
                    "options": [
                        {
                            "text": {"type": "plain_text", "text": "Auto"},
                            "value": "auto",
                        },
                        {
                            "text": {"type": "plain_text", "text": "Vibrant"},
                            "value": "vibrant",
                        },
                        {
                            "text": {"type": "plain_text", "text": "Pastel"},
                            "value": "pastel",
                        },
                        {
                            "text": {"type": "plain_text", "text": "Monochrome"},
                            "value": "monochrome",
                        },
                    ],
                },
                "label": {"type": "plain_text", "text": "Color Scheme"},
                "optional": True,
            },
            {
                "type": "input",
                "block_id": "tone",
                "element": {
                    "type": "static_select",
                    "action_id": "tone_select",
                    "initial_option": {
                        "text": {"type": "plain_text", "text": "Fun"},
                        "value": "fun",
                    },
                    "options": [
                        {"text": {"type": "plain_text", "text": "Fun"}, "value": "fun"},
                        {
                            "text": {"type": "plain_text", "text": "Professional"},
                            "value": "professional",
                        },
                        {
                            "text": {"type": "plain_text", "text": "Quirky"},
                            "value": "quirky",
                        },
                        {
                            "text": {"type": "plain_text", "text": "Serious"},
                            "value": "serious",
                        },
                    ],
                },
                "label": {"type": "plain_text", "text": "Tone"},
                "optional": True,
            },
            {
                "type": "input",
                "block_id": "share_location",
                "element": {
                    "type": "static_select",
                    "action_id": "share_location_select",
                    "initial_option": {
                        "text": {"type": "plain_text", "text": "Current Channel"},
                        "value": "channel",
                    },
                    "options": [
                        {
                            "text": {"type": "plain_text", "text": "Current Channel"},
                            "value": "channel",
                        },
                        {
                            "text": {"type": "plain_text", "text": "Workspace"},
                            "value": "workspace",
                        },
                        {
                            "text": {"type": "plain_text", "text": "Private"},
                            "value": "private",
                        },
                    ],
                },
                "label": {"type": "plain_text", "text": "Share Location"},
                "optional": True,
            },
            {
                "type": "input",
                "block_id": "instruction_visibility",
                "element": {
                    "type": "static_select",
                    "action_id": "visibility_select",
                    "initial_option": {
                        "text": {"type": "plain_text", "text": "Show Description"},
                        "value": "show",
                    },
                    "options": [
                        {
                            "text": {"type": "plain_text", "text": "Show Description"},
                            "value": "show",
                        },
                        {
                            "text": {"type": "plain_text", "text": "Hide Description"},
                            "value": "hide",
                        },
                    ],
                },
                "label": {"type": "plain_text", "text": "Instruction Visibility"},
                "optional": True,
            },
            {
                "type": "input",
                "block_id": "image_size",
                "element": {
                    "type": "static_select",
                    "action_id": "size_select",
                    "initial_option": {
                        "text": {"type": "plain_text", "text": "512x512 (Recommended)"},
                        "value": "512",
                    },
                    "options": [
                        {
                            "text": {
                                "type": "plain_text",
                                "text": "512x512 (Recommended)",
                            },
                            "value": "512",
                        },
                        {
                            "text": {"type": "plain_text", "text": "256x256"},
                            "value": "256",
                        },
                        {
                            "text": {"type": "plain_text", "text": "128x128"},
                            "value": "128",
                        },
                        {
                            "text": {"type": "plain_text", "text": "64x64"},
                            "value": "64",
                        },
                    ],
                },
                "label": {"type": "plain_text", "text": "Image Size"},
                "optional": True,
            },
        ]

    async def _build_modern_modal(self, slack_message: SlackMessage) -> dict[str, Any]:
        """Return the modern modal view definition."""
        metadata = {
            "message_text": slack_message.text,
            "user_id": slack_message.user_id,
            "channel_id": slack_message.channel_id,
            "timestamp": slack_message.timestamp,
            "team_id": slack_message.team_id,
        }

        # Start with basic blocks
        blocks = [
            # Preview section
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": " \n\n🎨\n\n*Preview*",
                },
            },
            {"type": "divider"},
            {
                "type": "input",
                "block_id": "emoji_name",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "name",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "e.g., coding_wizard",
                    },
                },
                "label": {"type": "plain_text", "text": "Emoji Name"},
                "hint": {
                    "type": "plain_text",
                    "text": "This will become :coding_wizard:",
                },
            },
            {
                "type": "input",
                "block_id": "emoji_description",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "description",
                    "multiline": True,
                    "placeholder": {
                        "type": "plain_text",
                        "text": "e.g., A retro computer terminal with green text",
                    },
                },
                "label": {"type": "plain_text", "text": "Description"},
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "🎨 *Style*\u2003\u2003\u2003\u2003⚡ *Detail*",
                },
            },
            {
                "type": "actions",
                "block_id": "style_preferences",
                "elements": [
                    {
                        "type": "static_select",
                        "action_id": "style_select",
                        "initial_option": {
                            "text": {"type": "plain_text", "text": "Cartoon"},
                            "value": "cartoon",
                        },
                        "options": [
                            {
                                "text": {"type": "plain_text", "text": "Cartoon"},
                                "value": "cartoon",
                            },
                            {
                                "text": {"type": "plain_text", "text": "Realistic"},
                                "value": "realistic",
                            },
                            {
                                "text": {
                                    "type": "plain_text",
                                    "text": "Minimalist",
                                },
                                "value": "minimalist",
                            },
                            {
                                "text": {"type": "plain_text", "text": "Pixel Art"},
                                "value": "pixel",
                            },
                        ],
                    },
                    {
                        "type": "static_select",
                        "action_id": "detail_select",
                        "initial_option": {
                            "text": {"type": "plain_text", "text": "Simple"},
                            "value": "simple",
                        },
                        "options": [
                            {
                                "text": {"type": "plain_text", "text": "Simple"},
                                "value": "simple",
                            },
                            {
                                "text": {"type": "plain_text", "text": "Detailed"},
                                "value": "detailed",
                            },
                        ],
                    },
                ],
            },
            {"type": "divider"},
            {
                "type": "actions",
                "block_id": "toggle_advanced",
                "elements": [
                    {
                        "type": "button",
                        "action_id": "toggle_advanced",
                        "text": {
                            "type": "plain_text",
                            "text": "⚙️ Advanced Options",
                        },
                        "value": "show",
                    }
                ],
            },
        ]

        return {
            "type": "modal",
            "callback_id": "emoji_creation_modal",
            "title": {"type": "plain_text", "text": "Create Emoji"},
            "blocks": blocks,
            "submit": {"type": "plain_text", "text": "✨ Generate"},
            "private_metadata": json.dumps(metadata),
        }

    async def _build_modern_modal_with_advanced(
        self, slack_message: SlackMessage, show_advanced: bool = False
    ) -> dict[str, Any]:
        """Build modal with optional advanced fields."""
        # Get base modal
        modal = await self._build_modern_modal(slack_message)

        if show_advanced:
            # Find the toggle button index
            toggle_index = -1
            for i, block in enumerate(modal["blocks"]):
                if block.get("block_id") == "toggle_advanced":
                    toggle_index = i
                    break

            if toggle_index >= 0:
                # Insert advanced blocks before the toggle button
                advanced_blocks = self._get_advanced_option_blocks()
                modal["blocks"][toggle_index:toggle_index] = advanced_blocks

                # Update button text and value
                modal["blocks"][toggle_index + len(advanced_blocks)]["elements"][0][
                    "text"
                ]["text"] = "⚙️ Hide Advanced Options"
                modal["blocks"][toggle_index + len(advanced_blocks)]["elements"][0][
                    "value"
                ] = "hide"

        return modal

    async def _open_emoji_creation_modal(
        self, slack_message: SlackMessage, trigger_id: str
    ) -> None:
        """Open the emoji creation modal using the modern design."""
        modal_view = await self._build_modern_modal(slack_message)

        self._logger.info(
            "Opening emoji creation modal", extra={"trigger_id": trigger_id}
        )
        await self._slack_repo.open_modal(trigger_id=trigger_id, view=modal_view)

    async def handle_block_actions(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Handle interactive block actions (button clicks, select menus, etc.)."""
        # For toggle advanced options button
        actions = payload.get("actions", [])

        for action in actions:
            if action.get("action_id") == "toggle_advanced":
                # Get current view
                view = payload.get("view", {})
                current_value = action.get("value", "show")

                # Parse metadata to rebuild modal
                try:
                    metadata = json.loads(view.get("private_metadata", "{}"))
                    slack_message = SlackMessage(
                        text=metadata["message_text"],
                        user_id=metadata["user_id"],
                        channel_id=metadata["channel_id"],
                        timestamp=metadata["timestamp"],
                        team_id=metadata["team_id"],
                    )

                    # Build modal with toggled state
                    show_advanced = current_value == "show"
                    new_modal = await self._build_modern_modal_with_advanced(
                        slack_message, show_advanced=show_advanced
                    )

                    # Update the modal
                    await self._slack_repo.update_modal(
                        view_id=view.get("id", ""), view=new_modal
                    )
                except Exception:
                    self._logger.exception("Failed to handle toggle action")

        # Acknowledge the action
        return {}
