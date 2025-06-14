"""Slack repository protocol for domain layer."""

from typing import Dict, Any, Protocol


class SlackRepository(Protocol):
    """Protocol for Slack API operations."""

    async def open_modal(self, trigger_id: str, view: Dict[str, Any]) -> None:
        """Open modal dialog in Slack."""
        ...