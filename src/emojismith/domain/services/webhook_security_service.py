"""Domain service for webhook security validation."""

from emojismith.domain.repositories.signature_validator import SignatureValidator
from emojismith.domain.value_objects.webhook_request import WebhookRequest


class WebhookSecurityService:
    """Domain service for validating webhook request authenticity."""

    def __init__(self, signature_validator: SignatureValidator) -> None:
        """Initialize webhook security service.

        Args:
            signature_validator: Protocol implementation for signature validation
        """
        self._signature_validator = signature_validator

    def is_authentic_webhook(self, request: WebhookRequest) -> bool:
        """Determine if a webhook request is authentic.

        This encapsulates the domain logic for webhook security, delegating
        the technical signature validation to the injected validator.

        Args:
            request: The webhook request to validate

        Returns:
            True if the webhook request is authentic, False otherwise
        """
        return self._signature_validator.validate_signature(request)
