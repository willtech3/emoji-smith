"""Protocol for notifying the requesting user about a job outcome."""

from typing import Protocol


class UserNotificationRepository(Protocol):
    """Sends a private status message to the user who requested an emoji."""

    async def notify_user(
        self,
        *,
        user_id: str,
        channel_id: str,
        text: str,
        thread_ts: str | None = None,
    ) -> bool:
        """Deliver a private message to the user.

        Returns:
            True when the message was delivered, False otherwise. Implementations
            must not raise: notifications are best-effort.
        """
        ...
