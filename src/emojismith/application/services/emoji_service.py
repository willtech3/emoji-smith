"""Emoji creation service for orchestrating the workflow."""

import json
import logging
import re
from typing import Dict, Any, Optional
from emojismith.domain.entities.slack_message import SlackMessage
from shared.domain.entities import EmojiGenerationJob
from emojismith.domain.repositories.slack_repository import SlackRepository
from emojismith.domain.repositories.job_queue_repository import JobQueueRepository
from emojismith.domain.services.generation_service import EmojiGenerationService
from emojismith.domain.services.emoji_sharing_service import (
    EmojiSharingService,
    EmojiSharingContext,
    WorkspaceType,
)

try:
    from emojismith.infrastructure.slack.slack_file_sharing import (
        SlackFileSharingRepository,
    )
except ImportError:
    # For tests when aiohttp is not available
    SlackFileSharingRepository = None  # type: ignore
from emojismith.domain.value_objects.emoji_specification import EmojiSpecification
from shared.domain.value_objects import (
    EmojiStylePreferences,
    EmojiSharingPreferences,
)


class EmojiCreationService:
    """Service for orchestrating emoji creation workflow."""

    _logger = logging.getLogger(__name__)

    def __init__(
        self,
        slack_repo: SlackRepository,
        emoji_generator: EmojiGenerationService,
        job_queue: Optional[JobQueueRepository] = None,
        file_sharing_repo: Optional[Any] = None,
        sharing_service: Optional[EmojiSharingService] = None,
    ) -> None:
        self._slack_repo = slack_repo
        self._emoji_generator = emoji_generator
        self._job_queue = job_queue
        self._file_sharing_repo = file_sharing_repo
        self._sharing_service = sharing_service or EmojiSharingService()

    async def initiate_emoji_creation(
        self, message: SlackMessage, trigger_id: str
    ) -> None:
        """Initiate emoji creation process by opening modal dialog."""
        # Prepare metadata including thread info if present
        metadata = {
            "message_text": message.text,
            "user_id": message.user_id,
            "channel_id": message.channel_id,
            "timestamp": message.timestamp,
            "team_id": message.team_id,
        }

        # Include thread timestamp if message is in a thread
        if hasattr(message, "thread_ts") and message.thread_ts:
            metadata["thread_ts"] = message.thread_ts

        # Build share location options
        share_options = []

        # If in thread, default to sharing in that thread
        if metadata.get("thread_ts"):
            share_options.extend(
                [
                    {
                        "text": {"type": "plain_text", "text": "This thread"},
                        "value": "thread",
                    },
                    {
                        "text": {"type": "plain_text", "text": "New thread"},
                        "value": "new_thread",
                    },
                ]
            )
        else:
            # Not in thread, default to new thread
            share_options.append(
                {
                    "text": {"type": "plain_text", "text": "New thread"},
                    "value": "new_thread",
                }
            )

        share_options.extend(
            [
                {
                    "text": {
                        "type": "plain_text",
                        "text": "Original channel (no thread)",
                    },
                    "value": "original_channel",
                },
                {
                    "text": {"type": "plain_text", "text": "Direct message"},
                    "value": "dm",
                },
            ]
        )

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
                            "text": (
                                "e.g., 'A retro computer terminal with green text on "
                                "black background'"
                            ),
                        },
                        "multiline": False,
                    },
                    "label": {
                        "type": "plain_text",
                        "text": "Emoji Description",
                    },
                },
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": "*Style Preferences*"},
                },
                {"type": "divider"},
                {
                    "type": "input",
                    "block_id": "style_type",
                    "element": {
                        "type": "static_select",
                        "action_id": "style_select",
                        "placeholder": {"type": "plain_text", "text": "Style"},
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
                                "text": {"type": "plain_text", "text": "Minimalist"},
                                "value": "minimalist",
                            },
                            {
                                "text": {"type": "plain_text", "text": "Pixel Art"},
                                "value": "pixel_art",
                            },
                        ],
                        "initial_option": {
                            "text": {"type": "plain_text", "text": "Cartoon"},
                            "value": "cartoon",
                        },
                    },
                    "label": {"type": "plain_text", "text": "Style"},
                },
                {
                    "type": "input",
                    "block_id": "color_scheme",
                    "element": {
                        "type": "static_select",
                        "action_id": "color_select",
                        "placeholder": {"type": "plain_text", "text": "Color scheme"},
                        "options": [
                            {
                                "text": {"type": "plain_text", "text": "Bright"},
                                "value": "bright",
                            },
                            {
                                "text": {"type": "plain_text", "text": "Muted"},
                                "value": "muted",
                            },
                            {
                                "text": {"type": "plain_text", "text": "Monochrome"},
                                "value": "monochrome",
                            },
                            {
                                "text": {"type": "plain_text", "text": "Auto"},
                                "value": "auto",
                            },
                        ],
                        "initial_option": {
                            "text": {"type": "plain_text", "text": "Auto"},
                            "value": "auto",
                        },
                    },
                    "label": {"type": "plain_text", "text": "Color Scheme"},
                },
                {
                    "type": "input",
                    "block_id": "detail_level",
                    "element": {
                        "type": "static_select",
                        "action_id": "detail_select",
                        "placeholder": {"type": "plain_text", "text": "Detail"},
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
                        "initial_option": {
                            "text": {"type": "plain_text", "text": "Simple"},
                            "value": "simple",
                        },
                    },
                    "label": {"type": "plain_text", "text": "Detail Level"},
                },
                {
                    "type": "input",
                    "block_id": "tone",
                    "element": {
                        "type": "static_select",
                        "action_id": "tone_select",
                        "placeholder": {"type": "plain_text", "text": "Tone"},
                        "options": [
                            {
                                "text": {"type": "plain_text", "text": "Fun"},
                                "value": "fun",
                            },
                            {
                                "text": {"type": "plain_text", "text": "Neutral"},
                                "value": "neutral",
                            },
                            {
                                "text": {"type": "plain_text", "text": "Expressive"},
                                "value": "expressive",
                            },
                        ],
                        "initial_option": {
                            "text": {"type": "plain_text", "text": "Fun"},
                            "value": "fun",
                        },
                    },
                    "label": {"type": "plain_text", "text": "Tone"},
                },
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": "*Sharing Options*"},
                },
                {"type": "divider"},
                {
                    "type": "input",
                    "block_id": "share_location",
                    "element": {
                        "type": "static_select",
                        "action_id": "share_location_select",
                        "placeholder": {
                            "type": "plain_text",
                            "text": "Where to share",
                        },
                        "options": share_options,
                        "initial_option": share_options[0],  # Default to channel
                    },
                    "label": {
                        "type": "plain_text",
                        "text": "Share Location",
                    },
                    "hint": {
                        "type": "plain_text",
                        "text": "Where the emoji file will be shared",
                    },
                },
                {
                    "type": "input",
                    "block_id": "instruction_visibility",
                    "element": {
                        "type": "static_select",
                        "action_id": "visibility_select",
                        "placeholder": {
                            "type": "plain_text",
                            "text": "Who sees instructions",
                        },
                        "options": [
                            {
                                "text": {"type": "plain_text", "text": "Everyone"},
                                "value": "everyone",
                            },
                            {
                                "text": {"type": "plain_text", "text": "Just me"},
                                "value": "requester_only",
                            },
                        ],
                        "initial_option": {
                            "text": {"type": "plain_text", "text": "Everyone"},
                            "value": "everyone",
                        },
                    },
                    "label": {
                        "type": "plain_text",
                        "text": "Instruction Visibility",
                    },
                    "hint": {
                        "type": "plain_text",
                        "text": "Who can see the upload instructions",
                    },
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
                                    "text": "Emoji size (128x128)",
                                },
                                "value": "emoji_size",
                            },
                            {
                                "text": {
                                    "type": "plain_text",
                                    "text": "Full size (1024x1024)",
                                },
                                "value": "full_size",
                            },
                        ],
                        "initial_option": {
                            "text": {
                                "type": "plain_text",
                                "text": "Emoji size (128x128)",
                            },
                            "value": "emoji_size",
                        },
                    },
                    "label": {
                        "type": "plain_text",
                        "text": "Image Size",
                    },
                    "hint": {
                        "type": "plain_text",
                        "text": "Size of the shared image file",
                    },
                },
            ],
            "submit": {"type": "plain_text", "text": "Generate Emoji"},
            "private_metadata": json.dumps(metadata),
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
            emoji_name = state["emoji_name"]["name"]["value"]
            share_location = state["share_location"]["share_location_select"][
                "selected_option"
            ]["value"]
            visibility = state["instruction_visibility"]["visibility_select"][
                "selected_option"
            ]["value"]
            image_size = state["image_size"]["size_select"]["selected_option"]["value"]
            try:
                style_type = state["style_type"]["style_select"]["selected_option"][
                    "value"
                ]
                color_scheme = state["color_scheme"]["color_select"]["selected_option"][
                    "value"
                ]
                detail_level = state["detail_level"]["detail_select"][
                    "selected_option"
                ]["value"]
                tone = state["tone"]["tone_select"]["selected_option"]["value"]
            except KeyError as e:
                self._logger.warning(f"Missing style preference: {e}")
                # Use safe defaults
                style_type, color_scheme, detail_level, tone = (
                    "cartoon",
                    "auto",
                    "simple",
                    "fun",
                )
            metadata = json.loads(view.get("private_metadata", "{}"))
            if not re.fullmatch(r"[a-z0-9_]+", emoji_name):
                raise ValueError(
                    "Emoji name must contain only lowercase letters, "
                    "numbers, and underscores"
                )
            if len(emoji_name) > 32:
                raise ValueError("Emoji name must be 32 characters or less")
        except (KeyError, json.JSONDecodeError) as exc:
            self._logger.exception("Malformed modal submission payload")
            raise ValueError("Malformed modal submission payload") from exc

        self._logger.info(
            "Processing modal submission",
            extra={
                "description": description,
                "share_location": share_location,
                "visibility": visibility,
                "image_size": image_size,
                "style_type": style_type,
                "color_scheme": color_scheme,
                "detail_level": detail_level,
                "tone": tone,
            },
        )

        # Create sharing preferences from user selections
        thread_ts = metadata.get("thread_ts") if share_location == "thread" else None
        sharing_preferences = EmojiSharingPreferences.from_form_values(
            share_location=share_location,
            instruction_visibility=visibility,
            image_size=image_size,
            thread_ts=thread_ts,
        )
        style_preferences = EmojiStylePreferences.from_form_values(
            style_type=style_type,
            color_scheme=color_scheme,
            detail_level=detail_level,
            tone=tone,
        )

        # Extract metadata from modal
        if self._job_queue:
            # Create job entity in application service
            job = EmojiGenerationJob.create_new(
                message_text=metadata["message_text"],
                user_description=description,
                user_id=metadata["user_id"],
                channel_id=metadata["channel_id"],
                timestamp=metadata["timestamp"],
                team_id=metadata["team_id"],
                sharing_preferences=sharing_preferences,
                thread_ts=metadata.get("thread_ts"),
                emoji_name=emoji_name,
                style_preferences=style_preferences,
            )
            # Queue job for background processing
            await self._job_queue.enqueue_job(job)
            self._logger.info(
                "Queued emoji generation job",
                extra={"job_id": job.job_id, "description": description},
            )
        else:
            # Fallback to synchronous processing for development
            await self.process_emoji_generation_job_dict(
                {
                    **metadata,
                    "user_description": description,
                    "emoji_name": emoji_name,
                    "sharing_preferences": sharing_preferences.to_dict(),
                    "style_preferences": style_preferences.to_dict(),
                }
            )

        return {"response_action": "clear"}

    async def process_emoji_generation_job(self, job: EmojiGenerationJob) -> None:
        """Process emoji generation job from background worker."""
        self._logger.info(
            "Processing emoji generation job",
            extra={"job_id": job.job_id, "user_id": job.user_id},
        )

        spec = EmojiSpecification(
            description=job.user_description,
            context=job.message_text,
            style=job.style_preferences,
        )
        # Use provided emoji name, sanitize for Slack (max 32 chars)
        name = job.emoji_name.replace(" ", "_").lower()[:32]
        emoji = await self._emoji_generator.generate(spec, name)

        # Determine workspace type (could be cached or configured)
        workspace_type = await self._detect_workspace_type()

        # Create sharing context
        from emojismith.domain.entities.slack_message import SlackMessage

        original_message = SlackMessage(
            text=job.message_text,
            user_id=job.user_id,
            channel_id=job.channel_id,
            timestamp=job.timestamp,
            team_id=job.team_id,
        )

        context = EmojiSharingContext(
            emoji=emoji,
            original_message=original_message,
            preferences=job.sharing_preferences
            or EmojiSharingPreferences.default_for_context(
                is_in_thread=bool(
                    job.sharing_preferences and job.sharing_preferences.thread_ts
                ),
                thread_ts=(
                    job.sharing_preferences.thread_ts
                    if job.sharing_preferences
                    else None
                ),
            ),
            workspace_type=workspace_type,
        )

        # Determine sharing strategy (for future use with strategy pattern)
        _ = self._sharing_service.determine_sharing_strategy(context)

        if workspace_type == WorkspaceType.ENTERPRISE_GRID:
            # Try direct upload for Enterprise Grid
            uploaded = await self._slack_repo.upload_emoji(
                name=name, image_data=emoji.image_data
            )
            if uploaded:
                # Add reaction if upload succeeded
                try:
                    await self._slack_repo.add_emoji_reaction(
                        emoji_name=name,
                        channel_id=job.channel_id,
                        timestamp=job.timestamp,
                    )
                except Exception as e:
                    self._logger.error(f"Failed to add emoji reaction: {e}")
        else:
            # Use file sharing for non-Enterprise workspaces
            if self._file_sharing_repo:
                result = await self._file_sharing_repo.share_emoji_file(
                    emoji=emoji,
                    channel_id=job.channel_id,
                    preferences=context.preferences,
                    requester_user_id=job.user_id,
                    original_message_ts=job.timestamp,
                )
                if result.success:
                    self._logger.info(
                        "Successfully shared emoji file",
                        extra={
                            "emoji_name": name,
                            "thread_ts": result.thread_ts,
                            "file_url": result.file_url,
                        },
                    )
                else:
                    self._logger.error(f"Failed to share emoji file: {result.error}")

        self._logger.info(
            "Successfully processed emoji generation job",
            extra={"job_id": job.job_id, "emoji_name": name},
        )

    async def _detect_workspace_type(self) -> WorkspaceType:
        """Detect workspace type based on available permissions."""
        # For now, we assume standard workspace since Enterprise Grid is rare
        # In production, this could check API permissions or be configured
        return WorkspaceType.STANDARD

    async def process_emoji_generation_job_dict(self, job_data: Dict[str, Any]) -> None:
        """Generate emoji using dict payload, upload to Slack, and add reaction."""
        # Convert dict to job entity for consistent processing
        job = EmojiGenerationJob.create_new(
            message_text=job_data["message_text"],
            user_description=job_data["user_description"],
            user_id=job_data["user_id"],
            channel_id=job_data["channel_id"],
            timestamp=job_data["timestamp"],
            team_id=job_data["team_id"],
            sharing_preferences=(
                EmojiSharingPreferences.from_dict(job_data["sharing_preferences"])
                if job_data.get("sharing_preferences")
                else EmojiSharingPreferences.default_for_context()
            ),
            style_preferences=(
                EmojiStylePreferences.from_dict(job_data["style_preferences"])
                if job_data.get("style_preferences")
                else EmojiStylePreferences()
            ),
            thread_ts=job_data.get("thread_ts"),
            emoji_name=job_data["emoji_name"],
        )

        # Process using the main method
        await self.process_emoji_generation_job(job)
