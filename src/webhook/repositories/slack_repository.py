"""Slack repository interface for webhook package."""

from abc import ABC, abstractmethod
from typing import Dict, Any


class SlackRepository(ABC):
    """Repository interface for Slack API operations."""

    @abstractmethod
    async def open_modal(self, trigger_id: str, view: Dict[str, Any]) -> None:
        """Open a modal dialog in Slack."""
        pass
