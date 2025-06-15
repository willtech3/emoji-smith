"""Slack signature validator infrastructure implementation."""

import os
import hmac
import hashlib
import time
from emojismith.domain.repositories.signature_validator import SignatureValidator
from emojismith.domain.value_objects.webhook_request import WebhookRequest


class SlackSignatureValidator(SignatureValidator):
    """Infrastructure implementation of Slack webhook signature validation."""

    def __init__(self) -> None:
        """Initialize Slack signature validator."""
        self._signing_secret = os.getenv("SLACK_SIGNING_SECRET")

    def validate_signature(self, request: WebhookRequest) -> bool:
        """Validate Slack webhook signature using HMAC-SHA256.

        Implements Slack's signature verification algorithm:
        1. Check timestamp to prevent replay attacks (5-minute window)
        2. Create signature basestring: v0:{timestamp}:{body}
        3. Compute HMAC-SHA256 with signing secret
        4. Compare signatures using secure comparison

        Args:
            request: Webhook request containing body, timestamp, and signature

        Returns:
            True if signature is valid, False otherwise
        """
        if not request.timestamp or not request.signature:
            return False

        if not self._signing_secret:
            return False

        # Check timestamp to prevent replay attacks (within 5 minutes)
        try:
            request_timestamp = int(request.timestamp)
            if abs(time.time() - request_timestamp) > 300:
                return False
        except (ValueError, TypeError):
            return False

        # Create signature basestring
        sig_basestring = f"v0:{request.timestamp}:{request.body.decode('utf-8')}"

        # Compute expected signature
        expected_signature = (
            "v0="
            + hmac.new(
                self._signing_secret.encode("utf-8"),
                sig_basestring.encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()
        )

        # Compare signatures securely
        return hmac.compare_digest(expected_signature, request.signature)
