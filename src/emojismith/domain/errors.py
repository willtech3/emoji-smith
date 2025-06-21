"""Domain-specific error types."""


class RateLimitExceededError(Exception):
    """Raised when an external service rate limit is exceeded."""
