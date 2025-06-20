from __future__ import annotations

import json
import urllib.parse
from typing import Any, Dict

from webhook.handler import WebhookHandler
from webhook.domain.webhook_request import WebhookRequest
from webhook.security.webhook_security_service import WebhookSecurityService


class UnauthorizedError(Exception):
    """Raised when webhook security validation fails."""


class SlackEventProcessor:
    """Dispatch Slack event payloads to the domain webhook handler."""

    def __init__(self, webhook_handler: WebhookHandler) -> None:
        self._webhook_handler = webhook_handler

    async def process(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        event_type = payload.get("type")
        if event_type == "message_action":
            return await self._webhook_handler.handle_message_action(payload)
        if event_type == "view_submission":
            return await self._webhook_handler.handle_modal_submission(payload)
        if event_type == "url_verification":
            return {"challenge": payload.get("challenge")}
        return {"status": "ignored"}


class SlackWebhookHandler:
    """Application layer handler for Slack webhooks."""

    def __init__(
        self,
        security_service: WebhookSecurityService,
        event_processor: SlackEventProcessor,
    ) -> None:
        self._security_service = security_service
        self._event_processor = event_processor

    async def handle_event(
        self, body: bytes, headers: Dict[str, str]
    ) -> Dict[str, Any]:
        """Validate and process a Slack webhook event."""
        timestamp = headers.get("X-Slack-Request-Timestamp")
        signature = headers.get("X-Slack-Signature")
        request = WebhookRequest(body=body, timestamp=timestamp, signature=signature)

        # Handle Slack URL verification without validation
        challenge = self._security_service.validate_url_verification(request)
        if challenge is not None:
            return {"challenge": challenge}

        if not self._security_service.is_authentic_webhook(request):
            raise UnauthorizedError()

        content_type = headers.get("content-type", "")
        if "application/x-www-form-urlencoded" in content_type:
            form_data = urllib.parse.parse_qs(body.decode("utf-8"))
            payload_str = form_data.get("payload", ["{}"])[0]
            payload = json.loads(payload_str)
        else:
            try:
                payload = json.loads(body.decode("utf-8"))
            except Exception:
                form_data = urllib.parse.parse_qs(body.decode("utf-8"))
                payload_str = form_data.get("payload", ["{}"])[0]
                payload = json.loads(payload_str)

        return await self._event_processor.process(payload)

    def health_check(self) -> Dict[str, str]:
        """Return basic health status."""
        return {"status": "healthy"}
