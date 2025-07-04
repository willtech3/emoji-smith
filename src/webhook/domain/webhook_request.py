"""Webhook request domain model."""

from dataclasses import dataclass


@dataclass
class WebhookRequest:
    """Represents a webhook request for security validation."""

    body: bytes
    timestamp: str | None
    signature: str | None
