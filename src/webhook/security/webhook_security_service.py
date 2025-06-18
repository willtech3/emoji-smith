"""Webhook security service for signature validation."""

import logging
from typing import Optional

from webhook.domain.webhook_request import WebhookRequest
from webhook.security.slack_signature_validator import (
    SlackSignatureValidator,
    MissingSigningSecretError,
)


class WebhookSecurityService:
    """Service for validating webhook security and handling security events."""

    def __init__(self, signature_validator: SlackSignatureValidator) -> None:
        """Initialize webhook security service.

        Args:
            signature_validator: SlackSignatureValidator instance for signature
                verification
        """
        self._signature_validator = signature_validator
        self._logger = logging.getLogger(__name__)

    def is_authentic_webhook(self, request: WebhookRequest) -> bool:
        """Validate that the webhook request is authentic.

        Performs comprehensive validation including:
        - Signature verification using HMAC-SHA256
        - Timestamp validation for replay attack prevention
        - Proper error handling and security logging

        Args:
            request: WebhookRequest containing body, timestamp, and signature

        Returns:
            True if webhook is authentic, False otherwise
        """
        if not request:
            self._logger.warning("Received null webhook request")
            return False

        if not request.body:
            self._logger.warning("Webhook request missing body")
            return False

        if not request.timestamp or not request.signature:
            self._logger.warning(
                "Webhook request missing required security headers",
                extra={
                    "has_timestamp": bool(request.timestamp),
                    "has_signature": bool(request.signature),
                },
            )
            return False

        try:
            # Delegate to signature validator
            is_valid = self._signature_validator.validate_request(request)

            # Log security events
            if is_valid:
                self._logger.debug("Webhook signature validation successful")
            else:
                self._logger.warning(
                    "Webhook signature validation failed",
                    extra={
                        "body_length": len(request.body),
                        "timestamp": request.timestamp,
                        "signature_prefix": (
                            request.signature[:20] if request.signature else None
                        ),
                    },
                )

            return is_valid

        except MissingSigningSecretError:
            self._logger.error("Webhook validation failed: Missing signing secret")
            return False
        except Exception as e:
            self._logger.exception(
                "Unexpected error during webhook validation",
                extra={"error": str(e)},
            )
            return False

    def validate_url_verification(self, request: WebhookRequest) -> Optional[str]:
        """Handle Slack URL verification challenge.

        During initial webhook setup, Slack sends a verification challenge
        that should be returned without signature validation.

        Args:
            request: WebhookRequest containing the challenge

        Returns:
            Challenge string if this is a valid URL verification, None otherwise
        """
        if not request or not request.body:
            return None

        try:
            import json

            # Parse JSON body
            payload = json.loads(request.body.decode("utf-8"))

            # Check if this is a URL verification request
            if payload.get("type") == "url_verification":
                challenge = payload.get("challenge")
                if challenge:
                    self._logger.info("Handling Slack URL verification challenge")
                    return str(challenge)
                else:
                    self._logger.warning("URL verification request missing challenge")

            return None

        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            self._logger.debug(f"Request body is not valid JSON: {e}")
            return None
        except Exception as e:
            self._logger.exception(f"Error processing URL verification: {e}")
            return None

    def should_skip_validation(self, request: WebhookRequest) -> bool:
        """Determine if signature validation should be skipped.

        Args:
            request: WebhookRequest to check

        Returns:
            True if validation should be skipped (e.g., for URL verification)
        """
        # Skip validation for URL verification challenges
        return self.validate_url_verification(request) is not None
