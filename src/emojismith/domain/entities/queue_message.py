"""Queue message entities for different operation types."""

from dataclasses import dataclass, replace
from enum import Enum
from typing import Any, ClassVar

from emojismith.domain.exceptions import RetryExceededError
from shared.domain.entities import EmojiGenerationJob


class MessageType(Enum):
    """Types of messages that can be queued."""

    EMOJI_GENERATION = "emoji_generation"


@dataclass
class QueueMessage:
    """Generic wrapper for all queue message types."""

    message_type: MessageType
    payload: EmojiGenerationJob
    retry_count: int = 0
    MAX_RETRIES: ClassVar[int] = 3

    def should_retry(self) -> bool:
        """Determine if message should be retried."""
        return self.retry_count < self.MAX_RETRIES

    def with_retry(self) -> "QueueMessage":
        """Create new message with incremented retry."""
        return replace(self, retry_count=self.retry_count + 1)

    def raise_if_exhausted(self) -> None:
        """Raise exception if retry attempts have been exhausted.

        Raises:
            RetryExceededError: If retry count has reached or exceeded MAX_RETRIES.
        """
        if not self.should_retry():
            raise RetryExceededError(
                f"Maximum retry attempts ({self.MAX_RETRIES}) exceeded "
                f"for message type {self.message_type.value}"
            )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for SQS serialization."""
        return {
            "message_type": self.message_type.value,
            "payload": self.payload.to_dict(),
            "retry_count": self.retry_count,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "QueueMessage":
        """Create from dictionary."""
        message_type = MessageType(data["message_type"])

        payload: EmojiGenerationJob
        if message_type == MessageType.EMOJI_GENERATION:
            payload = EmojiGenerationJob.from_dict(data["payload"])
        else:
            raise ValueError(f"Unknown message type: {message_type}")

        return cls(
            message_type=message_type,
            payload=payload,
            retry_count=data.get("retry_count", 0),
        )
