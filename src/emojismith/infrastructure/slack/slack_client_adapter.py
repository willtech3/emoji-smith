"""Adapter for Slack client to work with SlackMessageParser."""

from typing import Any

from slack_sdk.web.async_client import AsyncWebClient


class SlackClientAdapter:
    """Adapter to make AsyncWebClient compatible with SlackClientProtocol."""

    def __init__(self, slack_client: AsyncWebClient) -> None:
        """Initialize adapter with Slack client.

        Args:
            slack_client: The async Slack web client
        """
        self.slack_client = slack_client

    async def get_user_info_async(self, user_id: str) -> dict[str, Any]:
        """Get user information from Slack API asynchronously.

        Args:
            user_id: Slack user ID

        Returns:
            User information dictionary
        """
        try:
            response = await self.slack_client.users_info(user=user_id)
            if response["ok"] and "user" in response:
                user = response["user"]
                return {
                    "real_name": user.get("real_name", user.get("name", "Unknown User"))
                }
        except Exception:  # noqa: S110
            # Return default on any error - logging would be done at higher level
            # This is intentional - we want graceful degradation
            pass

        return {"real_name": "Unknown User"}

    def get_user_info(self, user_id: str) -> dict[str, Any]:
        """Get user information synchronously (for protocol compatibility).

        Note: This is a simplified version that returns cached or default data.
        For async operations, use get_user_info_async.

        Args:
            user_id: Slack user ID

        Returns:
            User information dictionary
        """
        # In a real implementation, this could use a cache or return defaults
        # Since the parser is synchronous but our client is async, we'll return
        # a default that can be enhanced later
        return {"real_name": f"User {user_id[-4:]}"}
