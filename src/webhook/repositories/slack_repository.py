"""Compatibility wrapper for Slack modal repository."""

from shared.domain.repositories.slack_repository import SlackModalRepository

SlackRepository = SlackModalRepository

__all__ = ["SlackRepository"]
