"""Queue message entities for different operation types."""

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Any, Union

from shared.domain.entities import EmojiGenerationJob


class MessageType(Enum):
    """Types of messages that can be queued."""

    EMOJI_GENERATION = "emoji_generation"


@dataclass
class QueueMessage:
    """Generic wrapper for all queue message types."""

    message_type: MessageType
    payload: EmojiGenerationJob

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for SQS serialization."""
        return {
            "message_type": self.message_type.value,
            "payload": self.payload.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "QueueMessage":
        """Create from dictionary."""
        message_type = MessageType(data["message_type"])

        payload: EmojiGenerationJob
        if message_type == MessageType.EMOJI_GENERATION:
            payload = EmojiGenerationJob.from_dict(data["payload"])
        else:
            raise ValueError(f"Unknown message type: {message_type}")

        return cls(message_type=message_type, payload=payload)
