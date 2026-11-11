"""Domain-specific error types."""


class RateLimitExceededError(Exception):
    """Raised when an external service rate limit is exceeded."""


class ImageGenerationRejectedError(Exception):
    """Raised when a provider refuses a prompt under its content policy.

    Retrying the same request cannot succeed, so callers should tell the user
    instead of retrying.
    """
