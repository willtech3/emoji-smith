"""Domain interface for signature validation."""

from typing import Protocol
from webhook.domain.webhook_request import WebhookRequest


class SignatureValidator(Protocol):
    """Protocol for webhook signature validation.

    This protocol defines the interface for validating webhook signatures
    according to the domain requirements, without being tied to any specific
    implementation details or external dependencies.
    """

    def validate(self, body: bytes, timestamp: str, signature: str) -> bool:
        """Validate webhook signature.

        Args:
            body: Raw request body as bytes
            timestamp: Request timestamp from security header
            signature: Signature from security header

        Returns:
            True if signature is valid, False otherwise
        """
        ...

    def validate_request(self, request: WebhookRequest) -> bool:
        """Validate webhook request using WebhookRequest object.

        Args:
            request: WebhookRequest containing body, timestamp, and signature

        Returns:
            True if signature is valid, False otherwise
        """
        ...
