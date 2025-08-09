"""Slack signature validator infrastructure implementation."""

import hashlib
import hmac
import logging
import os
import time

from emojismith.domain.protocols.signature_validator import SignatureValidator
from emojismith.domain.value_objects.webhook_request import WebhookRequest


class MissingSigningSecretError(Exception):
    """Raised when the Slack signing secret is not configured."""

    pass


class SlackSignatureValidator(SignatureValidator):
    """Infrastructure implementation of Slack webhook signature validation."""

    DEFAULT_REPLAY_WINDOW = 300  # 5 minutes in seconds

    def __init__(
        self,
        signing_secret: str | bytes | None = None,
        replay_window_seconds: int = DEFAULT_REPLAY_WINDOW,
    ) -> None:
        """Initialize Slack signature validator.

        Args:
            signing_secret: The Slack signing secret. If None, will attempt
                to load from SLACK_SIGNING_SECRET env var.
            replay_window_seconds: Time window in seconds for replay attack
                prevention.
        """
        # Normalize signing secret to string
        normalized_secret: str | None
        if isinstance(signing_secret, bytes | bytearray):
            normalized_secret = signing_secret.decode("utf-8")
        else:
            normalized_secret = signing_secret
        env_secret = os.getenv("SLACK_SIGNING_SECRET")
        resolved_secret: str | None
        if normalized_secret is not None:
            resolved_secret = normalized_secret
        else:
            resolved_secret = env_secret
        # Type: ensure internal attribute is always str
        self._signing_secret: str = resolved_secret or ""
        self._replay_window = replay_window_seconds
        self._logger = logging.getLogger(__name__)

    def validate_signature(self, request: WebhookRequest) -> bool:
        """Validate Slack webhook signature using HMAC-SHA256.

        Implements Slack's signature verification algorithm:
        1. Check timestamp to prevent replay attacks (configurable window)
        2. Create signature basestring: v0:{timestamp}:{body}
        3. Compute HMAC-SHA256 with signing secret
        4. Compare signatures using secure comparison

        Args:
            request: Webhook request containing body, timestamp, and signature

        Returns:
            True if signature is valid, False otherwise

        Raises:
            MissingSigningSecretError: If signing secret is not configured
        """
        if not request.timestamp or not request.signature:
            self._logger.warning("Missing timestamp or signature in webhook request")
            return False

        if not self._signing_secret:
            self._logger.error("Slack signing secret not configured")
            raise MissingSigningSecretError(
                "Slack signing secret not configured. "
                "Set SLACK_SIGNING_SECRET environment variable."
            )

        # Check timestamp to prevent replay attacks
        if request.timestamp_int is None:
            self._logger.warning("Invalid timestamp in webhook request")
            return False

        if abs(time.time() - request.timestamp_int) > self._replay_window:
            self._logger.warning("Webhook request timestamp outside replay window")
            return False

        # Create signature basestring using raw bytes (not decoded)
        # request.timestamp is guaranteed to be not None from checks above
        if not request.timestamp:
            return False
        sig_basestring = b"v0:" + request.timestamp.encode() + b":" + request.body

        # Compute expected signature
        expected_signature = self._compute_expected_signature(sig_basestring)

        # Compare signatures securely
        return hmac.compare_digest(expected_signature, request.signature)

    def _compute_expected_signature(self, sig_basestring: bytes) -> str:
        """Compute the expected signature for the given basestring.

        Args:
            sig_basestring: The signature basestring as bytes

        Returns:
            The expected signature string
        """
        # _signing_secret is guaranteed to be not None when this method is called
        if not self._signing_secret:
            raise MissingSigningSecretError("Signing secret is required")
        return (
            "v0="
            + hmac.new(
                self._signing_secret.encode("utf-8"),
                sig_basestring,
                hashlib.sha256,
            ).hexdigest()
        )
