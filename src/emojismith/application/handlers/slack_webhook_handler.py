from __future__ import annotations

import json
import logging
import urllib.parse
from typing import Any, Protocol

from emojismith.domain.services.webhook_security_service import WebhookSecurityService
from emojismith.domain.value_objects.webhook_request import WebhookRequest
from shared.domain.entities import EmojiGenerationJob, SlackMessage
from shared.domain.repositories import JobQueueProducer, SlackModalRepository
from shared.domain.value_objects import EmojiSharingPreferences


class SlackEventProcessor(Protocol):
    """Protocol for processing Slack event payloads."""

    async def process(self, body: bytes) -> dict[str, Any]:
        """Process a raw webhook body."""
        ...


class WebhookEventProcessor:
    """Default Slack event processor using application/infrastructure components."""

    def __init__(
        self, slack_repo: SlackModalRepository, job_queue: JobQueueProducer
    ) -> None:
        self._slack_repo = slack_repo
        self._job_queue = job_queue
        self._logger = logging.getLogger(__name__)

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
            return {}
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

        modal_view = {
            "type": "modal",
            "callback_id": "emoji_creation_modal",
            "title": {"type": "plain_text", "text": "Create Emoji"},
            "blocks": [
                {
                    "type": "input",
                    "block_id": "emoji_name",
                    "element": {"type": "plain_text_input", "action_id": "name"},
                    "label": {"type": "plain_text", "text": "Emoji Name"},
                },
                {
                    "type": "input",
                    "block_id": "emoji_description",
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "description",
                        "multiline": True,
                    },
                    "label": {"type": "plain_text", "text": "Description"},
                },
            ],
            "submit": {"type": "plain_text", "text": "✨ Generate"},
            "private_metadata": json.dumps(
                {
                    "message_text": slack_message.text,
                    "user_id": slack_message.user_id,
                    "channel_id": slack_message.channel_id,
                    "timestamp": slack_message.timestamp,
                    "team_id": slack_message.team_id,
                }
            ),
        }

        await self._slack_repo.open_modal(trigger_id=trigger_id, view=modal_view)
        return {"status": "ok"}

    async def _handle_modal_submission(self, payload: dict[str, Any]) -> dict[str, Any]:
        view = payload.get("view", {})
        state = view.get("state", {}).get("values", {})
        try:
            description = state["emoji_description"]["description"]["value"]
            emoji_name = state["emoji_name"]["name"]["value"]
        except Exception as exc:
            self._logger.error("Malformed modal submission: %s", exc)
            raise ValueError("Invalid modal submission payload") from exc

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
