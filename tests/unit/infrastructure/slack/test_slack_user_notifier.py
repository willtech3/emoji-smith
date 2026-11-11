"""Tests for private user notifications in Slack."""

from unittest.mock import AsyncMock

import pytest
from slack_sdk.errors import SlackApiError

from emojismith.infrastructure.slack.slack_user_notifier import SlackUserNotifier


@pytest.fixture()
def client() -> AsyncMock:
    return AsyncMock()


@pytest.mark.unit()
class TestSlackUserNotifier:
    async def test_notify_user_in_joined_channel_posts_ephemeral_message(self, client):
        delivered = await SlackUserNotifier(client).notify_user(
            user_id="U1", channel_id="C1", text="hello"
        )

        assert delivered is True
        client.chat_postEphemeral.assert_awaited_once_with(
            channel="C1", user="U1", text="hello"
        )
        client.chat_postMessage.assert_not_awaited()

    async def test_notify_user_when_bot_not_in_channel_sends_direct_message(
        self, client
    ):
        client.chat_postEphemeral.side_effect = SlackApiError(
            "not_in_channel", {"ok": False, "error": "not_in_channel"}
        )

        delivered = await SlackUserNotifier(client).notify_user(
            user_id="U1", channel_id="C1", text="hello"
        )

        assert delivered is True
        client.chat_postMessage.assert_awaited_once_with(channel="U1", text="hello")

    async def test_notify_user_when_slack_unavailable_returns_false(self, client):
        client.chat_postEphemeral.side_effect = RuntimeError("down")
        client.chat_postMessage.side_effect = RuntimeError("down")

        delivered = await SlackUserNotifier(client).notify_user(
            user_id="U1", channel_id="C1", text="hello"
        )

        assert delivered is False
