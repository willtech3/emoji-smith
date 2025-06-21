"""Domain-specific exceptions for Emoji Smith."""


class DomainException(Exception):
    """Base exception for all domain errors."""

    pass


class ValidationError(DomainException):
    """Raised when domain validation rules are violated."""

    pass


class RateLimitExceededError(DomainException):
    """Raised when rate limits are exceeded."""

    pass


class EmojiGenerationError(DomainException):
    """Raised when emoji generation fails."""

    pass


class PromptEnhancementError(DomainException):
    """Raised when prompt enhancement fails."""

    pass
