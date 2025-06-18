"""Protocol definitions for Slack repository interfaces."""

from typing import Any, Dict, Protocol


class SlackModalRepository(Protocol):
    """Operations for opening Slack modals."""

    async def open_modal(self, trigger_id: str, view: Dict[str, Any]) -> None: ...


class SlackEmojiRepository(Protocol):
    """Operations for uploading emoji and adding reactions."""

    async def upload_emoji(self, name: str, image_data: bytes) -> bool: ...

    async def add_emoji_reaction(
        self, emoji_name: str, channel_id: str, timestamp: str
    ) -> None: ...


class SlackRepository(SlackModalRepository, SlackEmojiRepository, Protocol):
    """Complete Slack repository interface."""

    pass
