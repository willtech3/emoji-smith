"""Webhook security service for signature validation."""

import logging
from webhook.domain.webhook_request import WebhookRequest
from webhook.security.slack_signature_validator import SlackSignatureValidator


class WebhookSecurityService:
    """Service for validating webhook security."""

    def __init__(self, signature_validator: SlackSignatureValidator) -> None:
        self._signature_validator = signature_validator
        self._logger = logging.getLogger(__name__)

    def is_authentic_webhook(self, request: WebhookRequest) -> bool:
        """Validate that the webhook request is authentic."""
        if not request.timestamp or not request.signature:
            self._logger.warning("Missing timestamp or signature in webhook request")
            return False

        try:
            return self._signature_validator.validate(
                body=request.body,
                timestamp=request.timestamp,
                signature=request.signature
            )
        except Exception as e:
            self._logger.exception(f"Error validating webhook signature: {e}")
            return False