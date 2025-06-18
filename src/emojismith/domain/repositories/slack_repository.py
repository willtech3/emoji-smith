"""Re-export Slack repository interfaces from shared domain."""

from shared.domain.repositories import (
    SlackModalRepository,
    SlackEmojiRepository,
    SlackRepository,
)

__all__ = ["SlackModalRepository", "SlackEmojiRepository", "SlackRepository"]
