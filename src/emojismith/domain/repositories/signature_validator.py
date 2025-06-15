"""Protocol for webhook signature validation."""

from typing import Protocol
from emojismith.domain.value_objects.webhook_request import WebhookRequest


class SignatureValidator(Protocol):
    """Protocol for validating webhook request signatures."""

    def validate_signature(self, request: WebhookRequest) -> bool:
        """Validate the signature of a webhook request.

        Args:
            request: The webhook request containing body, timestamp, and signature

        Returns:
            True if signature is valid, False otherwise
        """
        ...
