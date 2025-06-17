"""Queue message entities for different operation types."""

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Any, Union

from shared.domain.entities import EmojiGenerationJob
from emojismith.domain.entities.slack_message import SlackMessage


class MessageType(Enum):
    """Types of messages that can be queued."""

    EMOJI_GENERATION = "emoji_generation"
    MODAL_OPENING = "modal_opening"


@dataclass
class ModalOpeningMessage:
    """Message for opening Slack modal asynchronously."""

    message_id: str
    slack_message: SlackMessage
    trigger_id: str
    created_at: datetime

    @classmethod
    def create_new(
        cls,
        slack_message: SlackMessage,
        trigger_id: str,
    ) -> "ModalOpeningMessage":
        """Create a new modal opening message."""
        return cls(
            message_id=str(uuid.uuid4()),
            slack_message=slack_message,
            trigger_id=trigger_id,
            created_at=datetime.now(timezone.utc),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "message_id": self.message_id,
            "slack_message": {
                "text": self.slack_message.text,
                "user_id": self.slack_message.user_id,
                "channel_id": self.slack_message.channel_id,
                "timestamp": self.slack_message.timestamp,
                "team_id": self.slack_message.team_id,
            },
            "trigger_id": self.trigger_id,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ModalOpeningMessage":
        """Create from dictionary."""
        slack_msg_data = data["slack_message"]
        slack_message = SlackMessage(
            text=slack_msg_data["text"],
            user_id=slack_msg_data["user_id"],
            channel_id=slack_msg_data["channel_id"],
            timestamp=slack_msg_data["timestamp"],
            team_id=slack_msg_data["team_id"],
        )

        return cls(
            message_id=data["message_id"],
            slack_message=slack_message,
            trigger_id=data["trigger_id"],
            created_at=datetime.fromisoformat(data["created_at"]),
        )


@dataclass
class QueueMessage:
    """Generic wrapper for all queue message types."""

    message_type: MessageType
    payload: Union[EmojiGenerationJob, ModalOpeningMessage]

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

        payload: Union[EmojiGenerationJob, ModalOpeningMessage]
        if message_type == MessageType.EMOJI_GENERATION:
            payload = EmojiGenerationJob.from_dict(data["payload"])
        elif message_type == MessageType.MODAL_OPENING:
            payload = ModalOpeningMessage.from_dict(data["payload"])
        else:
            raise ValueError(f"Unknown message type: {message_type}")

        return cls(message_type=message_type, payload=payload)
