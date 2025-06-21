from __future__ import annotations

import json
import logging
import urllib.parse
from typing import Any, Dict, Protocol

from webhook.security.webhook_security_service import WebhookSecurityService
from webhook.domain.webhook_request import WebhookRequest
from webhook.handler import WebhookHandler


class SlackEventProcessor(Protocol):
    """Protocol for processing Slack event payloads."""

    async def process(self, body: bytes) -> Dict[str, Any]:
        """Process a raw webhook body."""
        ...


class WebhookEventProcessor:
    """Default Slack event processor using the legacy WebhookHandler."""

    def __init__(self, webhook_handler: WebhookHandler) -> None:
        self._webhook_handler = webhook_handler
        self._logger = logging.getLogger(__name__)

    async def process(self, body: bytes) -> Dict[str, Any]:
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
            return await self._webhook_handler.handle_message_action(payload)
        if event_type == "view_submission":
            return await self._webhook_handler.handle_modal_submission(payload)
        return {"status": "ignored"}


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

    def health_check(self) -> Dict[str, str]:
        """Return basic health information."""
        return {"status": "healthy"}

    async def handle_event(
        self, body: bytes, headers: Dict[str, str]
    ) -> Dict[str, Any]:
        """Validate and process an incoming Slack webhook event."""
        timestamp = headers.get("X-Slack-Request-Timestamp") or headers.get(
            "x-slack-request-timestamp"
        )
        signature = headers.get("X-Slack-Signature") or headers.get("x-slack-signature")

        request = WebhookRequest(body=body, timestamp=timestamp, signature=signature)

        if not body.startswith(b'{"type":"url_verification"'):
            if not self._security_service.is_authentic_webhook(request):
                raise UnauthorizedError("Invalid webhook signature")

        return await self._event_processor.process(body)
