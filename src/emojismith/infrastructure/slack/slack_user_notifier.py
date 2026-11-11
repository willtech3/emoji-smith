"""Slack implementation of private user notifications."""

import logging

from slack_sdk.web.async_client import AsyncWebClient


class SlackUserNotifier:
    """Tells the requesting user about a job outcome without posting publicly.

    An ephemeral message in the originating channel is preferred because it
    appears where the user is working. That fails when the bot is not a member
    of the channel (the usual reason a job could not be delivered), so a direct
    message is used as the fallback.
    """

    def __init__(self, slack_client: AsyncWebClient) -> None:
        self._client = slack_client
        self._logger = logging.getLogger(__name__)

    async def notify_user(
        self,
        *,
        user_id: str,
        channel_id: str,
        text: str,
        thread_ts: str | None = None,
    ) -> bool:
        try:
            if thread_ts:
                await self._client.chat_postEphemeral(
                    channel=channel_id, user=user_id, text=text, thread_ts=thread_ts
                )
            else:
                await self._client.chat_postEphemeral(
                    channel=channel_id, user=user_id, text=text
                )
            return True
        except Exception as exc:
            self._logger.warning(
                "Ephemeral notification failed, falling back to direct message: %s",
                exc,
            )

        try:
            await self._client.chat_postMessage(channel=user_id, text=text)
            return True
        except Exception as exc:
            self._logger.error("Could not notify user about job outcome: %s", exc)
            return False
