"""Domain-specific exceptions for Emoji Smith."""


class DomainError(Exception):
    """Base exception for all domain errors."""

    pass


class ValidationError(DomainError):
    """Raised when domain validation rules are violated."""

    pass


class RateLimitExceededError(DomainError):
    """Raised when rate limits are exceeded."""

    pass


class EmojiGenerationError(DomainError):
    """Raised when emoji generation fails."""

    pass


class PromptEnhancementError(DomainError):
    """Raised when prompt enhancement fails."""

    pass


class RetryExceededError(DomainError):
    """Raised when maximum retry attempts have been exceeded."""

    pass
