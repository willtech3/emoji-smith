from typing import Any, Dict, Protocol, runtime_checkable


@runtime_checkable
class SlackModalRepository(Protocol):
    """Modal operations for Slack."""

    async def open_modal(self, trigger_id: str, view: Dict[str, Any]) -> None: ...


@runtime_checkable
class SlackEmojiRepository(Protocol):
    """Emoji-related operations for Slack."""

    async def upload_emoji(self, name: str, image_data: bytes) -> bool: ...

    async def add_emoji_reaction(
        self, emoji_name: str, channel_id: str, timestamp: str
    ) -> None: ...


@runtime_checkable
class SlackRepository(SlackModalRepository, SlackEmojiRepository, Protocol):
    """Complete Slack repository interface."""

    pass
