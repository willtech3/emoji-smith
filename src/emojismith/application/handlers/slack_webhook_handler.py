from __future__ import annotations

import json
import urllib.parse
from typing import Any, Dict

from webhook.handler import WebhookHandler
from webhook.domain.webhook_request import WebhookRequest
from webhook.security.webhook_security_service import WebhookSecurityService


class UnauthorizedError(Exception):
    """Raised when a webhook request fails authentication."""


class SlackWebhookHandler:
    """Application layer handler orchestrating webhook processing."""

    def __init__(
        self, security_service: WebhookSecurityService, event_processor: WebhookHandler
    ) -> None:
        self._security_service = security_service
        self._event_processor = event_processor

    async def health_check(self) -> Dict[str, str]:
        """Return simple health check status."""
        return {"status": "healthy"}

    async def handle_event(
        self, body: bytes, headers: Dict[str, str]
    ) -> Dict[str, Any]:
        """Validate and process an incoming Slack event."""
        timestamp = headers.get("X-Slack-Request-Timestamp")
        signature = headers.get("X-Slack-Signature")
        content_type = headers.get("content-type", "")

        request = WebhookRequest(body=body, timestamp=timestamp, signature=signature)

        try:
            payload_type = json.loads(body.decode("utf-8")).get("type")
        except Exception:
            payload_type = None

        if payload_type != "url_verification":
            if not self._security_service.is_authentic_webhook(request):
                raise UnauthorizedError("Invalid webhook signature")

        if "application/x-www-form-urlencoded" in content_type:
            form_data = urllib.parse.parse_qs(body.decode("utf-8"))
            payload_str = form_data.get("payload", ["{}"])[0]
            payload = json.loads(payload_str)
        elif "application/json" in content_type:
            payload = json.loads(body.decode("utf-8"))
        else:
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
            return await self._event_processor.handle_message_action(payload)
        if event_type == "view_submission":
            return await self._event_processor.handle_modal_submission(payload)
        return {"status": "ignored"}
