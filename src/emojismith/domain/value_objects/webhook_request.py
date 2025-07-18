"""Webhook request value object."""

from dataclasses import dataclass


@dataclass(frozen=True)
class WebhookRequest:
    """Value object representing an incoming webhook request for security validation."""

    body: bytes
    timestamp: str | None
    signature: str | None

    # Parsed timestamp as integer for validation
    _timestamp_int: int | None = None

    def __post_init__(self) -> None:
        """Validate webhook request data."""
        if not self.body:
            raise ValueError("Webhook request body cannot be empty")

        # Validate and parse timestamp
        if self.timestamp is not None:
            if not isinstance(self.timestamp, str):
                raise ValueError("Webhook timestamp must be a string")
            if not self.timestamp.isdigit():
                raise ValueError("Webhook timestamp must contain only ASCII digits")
            try:
                # Use object.__setattr__ to set the parsed timestamp since
                # the dataclass is frozen
                object.__setattr__(self, "_timestamp_int", int(self.timestamp))
            except ValueError as e:
                raise ValueError("Webhook timestamp must be a valid integer") from e

        # Validate signature
        if self.signature is not None:
            if not isinstance(self.signature, str):
                raise ValueError("Webhook signature must be a string")
            if not self.signature:
                raise ValueError("Webhook signature cannot be empty")

    @property
    def timestamp_int(self) -> int | None:
        """Get the parsed timestamp as integer."""
        return self._timestamp_int
