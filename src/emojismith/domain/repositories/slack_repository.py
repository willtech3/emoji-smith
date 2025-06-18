"""Re-export SlackRepository protocol from shared package."""

from shared.domain.repositories.slack_repository import SlackRepository

__all__ = ["SlackRepository"]
