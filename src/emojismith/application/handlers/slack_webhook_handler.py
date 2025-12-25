from __future__ import annotations

import hashlib
import json
import logging
import re
import urllib.parse
from typing import Any, Protocol

from emojismith.application.modal_builder import EmojiCreationModalBuilder
from emojismith.domain.services.webhook_security_service import WebhookSecurityService
from emojismith.domain.value_objects.webhook_request import WebhookRequest
from shared.domain.entities import EmojiGenerationJob, SlackMessage
from shared.domain.repositories import JobQueueProducer, SlackModalRepository
from shared.domain.value_objects import (
    EmojiGenerationPreferences,
    EmojiSharingPreferences,
)


class SlackEventProcessor(Protocol):
    """Protocol for processing Slack event payloads."""

    async def process(self, body: bytes) -> dict[str, Any]:
        """Process a raw webhook body."""
        ...


class WebhookEventProcessor:
    """Default Slack event processor using application/infrastructure components."""

    def __init__(
        self,
        slack_repo: SlackModalRepository,
        job_queue: JobQueueProducer,
        google_enabled: bool = True,
    ) -> None:
        self._slack_repo = slack_repo
        self._job_queue = job_queue
        self._logger = logging.getLogger(__name__)

        # Configure modal builder providers for the Slack UI.
        #
        # The webhook Lambda is intentionally "thin" and does not receive AI provider
        # API keys (those belong in the worker Lambda). Provider availability is
        # therefore configured explicitly via dependency injection.
        google_available = google_enabled
        default_provider = "google_gemini" if google_enabled else "openai"

        self._modal_builder = EmojiCreationModalBuilder(
            default_provider=default_provider,
            google_available=google_available,
        )

    @staticmethod
    def _generate_emoji_name(description: str) -> str:
        """Generate a valid Slack emoji name from description.

        Creates a slugified name from the description with a short hash suffix
        for uniqueness. Result is lowercase, underscores only, max 32 chars.

        Example: "A happy dancing banana" -> "a_happy_dancing_banan_x7k2m"
        """
        # Keep only alphanumeric and spaces
        cleaned = re.sub(r"[^a-zA-Z0-9\s]", "", description)
        # Convert to lowercase and replace spaces with underscores
        slugified = cleaned.lower().strip().replace(" ", "_")
        # Remove consecutive underscores
        slugified = re.sub(r"_+", "_", slugified)
        # Strip leading/trailing underscores
        slugified = slugified.strip("_")

        # Generate short hash suffix for uniqueness (5 chars)
        hash_suffix = hashlib.sha256(description.encode()).hexdigest()[:5]

        # Truncate to leave room for underscore + 5-char suffix (max 32 total)
        max_base_len = 32 - 1 - len(hash_suffix)  # 26 chars
        if len(slugified) > max_base_len:
            slugified = slugified[:max_base_len].rstrip("_")

        return f"{slugified}_{hash_suffix}"

    async def process(self, body: bytes) -> dict[str, Any]:
        try:
            payload = json.loads(body.decode("utf-8"))
        except Exception:
            form_data = urllib.parse.parse_qs(body.decode("utf-8"))
            payload_str = form_data.get("payload", ["{}"])[0]
            payload = json.loads(payload_str)

        if payload.get("type") == "url_verification":
            return {"challenge": payload.get("challenge")}

        event_type = payload.get("type")
        if event_type == "message_action":
            return await self._handle_message_action(payload)
        if event_type == "view_submission":
            return await self._handle_modal_submission(payload)
        if event_type == "block_actions":
            return await self._handle_block_action(payload)
        return {"status": "ignored"}

    async def _handle_message_action(self, payload: dict[str, Any]) -> dict[str, Any]:
        message = payload.get("message", {})
        channel = payload.get("channel", {})
        team = payload.get("team", {})
        slack_message = SlackMessage(
            text=message.get("text", ""),
            user_id=message.get("user", ""),
            channel_id=channel.get("id", ""),
            timestamp=message.get("ts", ""),
            team_id=team.get("id", ""),
        )
        trigger_id = payload.get("trigger_id", "")

        # Build metadata for the modal
        metadata = {
            "message_text": slack_message.text,
            "user_id": slack_message.user_id,
            "channel_id": slack_message.channel_id,
            "timestamp": slack_message.timestamp,
            "team_id": slack_message.team_id,
        }

        # Use ModalBuilder for progressive disclosure - start with simple mode
        modal_view = self._modal_builder.build_collapsed_view(metadata)

        await self._slack_repo.open_modal(trigger_id=trigger_id, view=modal_view)
        return {"status": "ok"}

    async def _handle_block_action(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Handle interactive block actions (e.g., toggle button clicks)."""
        actions = payload.get("actions", [])
        view = payload.get("view", {})

        for action in actions:
            if action.get("action_id") == self._modal_builder.STYLE_TOGGLE_ACTION:
                # Get current metadata
                metadata = json.loads(view.get("private_metadata", "{}"))

                # Toggle between collapsed and expanded views
                if action.get("value") == "expand":
                    new_view = self._modal_builder.build_expanded_view(metadata)
                else:
                    new_view = self._modal_builder.build_collapsed_view(metadata)

                await self._slack_repo.update_modal(
                    view_id=view.get("id", ""), view=new_view
                )

        return {}

    async def _handle_modal_submission(self, payload: dict[str, Any]) -> dict[str, Any]:
        view = payload.get("view", {})
        state = view.get("state", {}).get("values", {})

        # Extract description (required)
        description = (
            state.get(self._modal_builder.DESCRIPTION_BLOCK, {})
            .get(self._modal_builder.DESCRIPTION_ACTION, {})
            .get("value", "")
        )

        if not description:
            return {
                "response_action": "errors",
                "errors": {
                    self._modal_builder.DESCRIPTION_BLOCK: "Please describe your emoji"
                },
            }

        # Extract emoji name (optional, auto-generate from description if empty)
        emoji_name = (
            state.get(self._modal_builder.EMOJI_NAME_BLOCK, {})
            .get(self._modal_builder.NAME_ACTION, {})
            .get("value", "")
        )
        if not emoji_name:
            emoji_name = self._generate_emoji_name(description)

        # Extract image provider (default based on availability)
        image_provider = (
            state.get(self._modal_builder.IMAGE_PROVIDER_BLOCK, {})
            .get(self._modal_builder.PROVIDER_ACTION, {})
            .get("selected_option", {})
            .get("value", self._modal_builder.default_provider)
        )

        # Extract advanced options
        background = (
            state.get(self._modal_builder.BACKGROUND_BLOCK, {})
            .get(self._modal_builder.BACKGROUND_ACTION, {})
            .get("selected_option", {})
            .get("value", "transparent")
        )
        quality = (
            state.get(self._modal_builder.QUALITY_BLOCK, {})
            .get(self._modal_builder.QUALITY_ACTION, {})
            .get("selected_option", {})
            .get("value", "high")
        )
        num_images = (
            state.get(self._modal_builder.NUM_IMAGES_BLOCK, {})
            .get(self._modal_builder.NUM_IMAGES_ACTION, {})
            .get("selected_option", {})
            .get("value", "1")
        )
        style_text = (
            state.get(self._modal_builder.STYLE_TEXT_BLOCK, {})
            .get(self._modal_builder.STYLE_TEXT_ACTION, {})
            .get("value", "")
        )

        # Create generation preferences from form values
        generation_preferences = EmojiGenerationPreferences.from_form_values(
            background=background,
            quality=quality,
            num_images=num_images,
            style_text=style_text,
        )

        metadata = json.loads(view.get("private_metadata", "{}"))

        sharing_preferences = EmojiSharingPreferences.from_form_values(
            share_location="channel",
            instruction_visibility="show",
            image_size="512",
            thread_ts=metadata.get("thread_ts"),
        )

        job = EmojiGenerationJob.create_new(
            user_description=description,
            message_text=metadata.get("message_text", ""),
            user_id=metadata.get("user_id", ""),
            channel_id=metadata.get("channel_id", ""),
            timestamp=metadata.get("timestamp", ""),
            team_id=metadata.get("team_id", ""),
            sharing_preferences=sharing_preferences,
            emoji_name=emoji_name,
            image_provider=image_provider,
            generation_preferences=generation_preferences,
        )

        await self._job_queue.enqueue_job(job)
        return {"response_action": "clear"}


class UnauthorizedError(Exception):
    """Raised when a webhook request fails authentication."""


class SlackWebhookHandler:
    """Application layer handler for Slack webhooks."""

    def __init__(
        self,
        security_service: WebhookSecurityService,
        event_processor: SlackEventProcessor,
    ) -> None:
        self._security_service = security_service
        self._event_processor = event_processor

    def health_check(self) -> dict[str, str]:
        """Return basic health information."""
        return {"status": "healthy"}

    async def handle_event(
        self, body: bytes, headers: dict[str, str]
    ) -> dict[str, Any]:
        """Validate and process an incoming Slack webhook event."""
        timestamp = headers.get("X-Slack-Request-Timestamp") or headers.get(
            "x-slack-request-timestamp"
        )
        signature = headers.get("X-Slack-Signature") or headers.get("x-slack-signature")
        request = WebhookRequest(body=body, timestamp=timestamp, signature=signature)

        if not body.startswith(
            b'{"type":"url_verification"'
        ) and not self._security_service.is_authentic_webhook(request):
            raise UnauthorizedError("Invalid webhook signature")

        return await self._event_processor.process(body)
