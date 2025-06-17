"""Slack signature validator for webhook security."""

import hashlib
import hmac
import time
import logging


class SlackSignatureValidator:
    """Validates Slack webhook signatures."""

    def __init__(self, signing_secret: str) -> None:
        self._signing_secret = signing_secret.encode()
        self._logger = logging.getLogger(__name__)

    def validate(self, body: bytes, timestamp: str, signature: str) -> bool:
        """Validate Slack webhook signature."""
        # Check timestamp freshness (within 5 minutes)
        current_time = int(time.time())
        request_time = int(timestamp)
        
        if abs(current_time - request_time) > 300:  # 5 minutes
            self._logger.warning("Webhook timestamp too old")
            return False

        # Create expected signature
        sig_basestring = f"v0:{timestamp}:".encode() + body
        expected_signature = "v0=" + hmac.new(
            self._signing_secret,
            sig_basestring,
            hashlib.sha256
        ).hexdigest()

        # Compare signatures securely
        return hmac.compare_digest(expected_signature, signature)