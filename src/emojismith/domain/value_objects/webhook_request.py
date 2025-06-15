"""Webhook request value object."""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class WebhookRequest:
    """Value object representing an incoming webhook request for security validation."""

    body: bytes
    timestamp: Optional[str]
    signature: Optional[str]

    def __post_init__(self) -> None:
        """Validate webhook request data."""
        if not self.body:
            raise ValueError("Webhook request body cannot be empty")
