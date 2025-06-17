"""Webhook request domain model."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class WebhookRequest:
    """Represents a webhook request for security validation."""
    
    body: bytes
    timestamp: Optional[str]
    signature: Optional[str]