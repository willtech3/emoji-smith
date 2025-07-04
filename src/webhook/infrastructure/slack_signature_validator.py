"""Slack signature validator implementation for webhook security."""

import hashlib
import hmac
import logging
import time

from webhook.domain.webhook_request import WebhookRequest


class MissingSigningSecretError(Exception):
    """Raised when the Slack signing secret is not configured."""

    pass


class SlackSignatureValidator:
    """Validates Slack webhook signatures using HMAC-SHA256.

    This implementation follows Slack's signature verification algorithm
    and includes replay attack prevention with configurable time windows.
    """

    DEFAULT_REPLAY_WINDOW = 300  # 5 minutes in seconds

    def __init__(
        self,
        *,
        signing_secret: bytes,
        replay_window_seconds: int = DEFAULT_REPLAY_WINDOW,
    ) -> None:
        """Initialize Slack signature validator.

        Args:
            signing_secret: The Slack signing secret as bytes for HMAC verification.
            replay_window_seconds: Time window in seconds for replay attack prevention.
        """
        self._signing_secret = signing_secret
        self._replay_window = replay_window_seconds
        self._logger = logging.getLogger(__name__)

    def validate(
        self, body: bytes, timestamp: str | None, signature: str | None
    ) -> bool:
        """Validate Slack webhook signature.

        Implements Slack's signature verification algorithm:
        1. Check timestamp to prevent replay attacks (configurable window)
        2. Create signature basestring: v0:{timestamp}:{body}
        3. Compute HMAC-SHA256 with signing secret
        4. Compare signatures using secure comparison (strips v0= prefix)

        Args:
            body: Raw request body as bytes
            timestamp: Request timestamp from X-Slack-Request-Timestamp header
            signature: Signature from X-Slack-Signature header (must start with v0=)

        Returns:
            True if signature is valid, False otherwise
        """
        if not timestamp or not signature:
            self._logger.warning("Missing timestamp or signature in webhook request")
            return False

        try:
            # Check timestamp freshness to prevent replay attacks
            current_time = int(time.time())
            request_time = int(timestamp)

            if abs(current_time - request_time) >= self._replay_window:
                self._logger.warning(
                    "Webhook request timestamp outside replay window",
                    extra={
                        "current_time": current_time,
                        "request_time": request_time,
                        "window": self._replay_window,
                    },
                )
                return False

            # Create signature basestring
            sig_basestring = f"v0:{timestamp}:".encode() + body

            # Compute expected signature
            expected_signature = self._compute_expected_signature(sig_basestring)

            # Strip v0= prefix from received signature for comparison
            if not signature.startswith("v0="):
                self._logger.warning("Signature does not have required v0= prefix")
                return False

            received_digest = signature[3:]  # Remove "v0=" prefix
            expected_digest = expected_signature[3:]  # Remove "v0=" prefix

            # Compare signatures securely (constant-time comparison)
            is_valid = hmac.compare_digest(expected_digest, received_digest)

            if not is_valid:
                self._logger.warning(
                    "Webhook signature validation failed",
                    extra={
                        "body_hash": hashlib.sha256(body).hexdigest()[
                            :8
                        ],  # Safe logging
                        "timestamp": timestamp,
                    },
                )

            return is_valid

        except (ValueError, TypeError) as e:
            self._logger.warning(f"Invalid timestamp format in webhook request: {e}")
            return False
        except Exception as e:
            self._logger.exception(f"Unexpected error during signature validation: {e}")
            return False

    def validate_request(self, request: WebhookRequest) -> bool:
        """Validate webhook request using WebhookRequest object.

        Args:
            request: WebhookRequest containing body, timestamp, and signature

        Returns:
            True if signature is valid, False otherwise
        """
        if not request.timestamp or not request.signature:
            return False

        return self.validate(
            body=request.body,
            timestamp=request.timestamp,
            signature=request.signature,
        )

    def _compute_expected_signature(self, sig_basestring: bytes) -> str:
        """Compute the expected signature for the given basestring.

        Args:
            sig_basestring: The signature basestring as bytes

        Returns:
            The expected signature string in format: v0=<hex_digest>
        """
        return (
            "v0="
            + hmac.new(
                self._signing_secret,
                sig_basestring,
                hashlib.sha256,
            ).hexdigest()
        )
