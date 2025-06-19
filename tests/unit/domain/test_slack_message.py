"""Tests for SlackMessage domain entity."""

import pytest
from shared.domain.entities.slack_message import SlackMessage


class TestSlackMessage:
    """Test SlackMessage domain entity."""

    def test_slack_message_creation_with_valid_data(self):
        """Test SlackMessage can be created with valid data."""
        message = SlackMessage(
            text="Just deployed on Friday afternoon!",
            user_id="U12345",
            channel_id="C67890",
            timestamp="1234567890.123456",
            team_id="T11111",
        )

        assert message.text == "Just deployed on Friday afternoon!"
        assert message.user_id == "U12345"
        assert message.channel_id == "C67890"
        assert message.timestamp == "1234567890.123456"
        assert message.team_id == "T11111"

    def test_slack_message_truncates_long_text(self):
        """Test SlackMessage truncates text longer than 1000 characters."""
        long_text = "a" * 1500
        message = SlackMessage(
            text=long_text,
            user_id="U12345",
            channel_id="C67890",
            timestamp="1234567890.123456",
            team_id="T11111",
        )

        assert len(message.text) == 1000
        assert message.text == "a" * 1000

    def test_slack_message_requires_user_id(self):
        """Test SlackMessage requires a user_id."""
        with pytest.raises(ValueError, match="user_id is required"):
            SlackMessage(
                text="Test message",
                user_id="",
                channel_id="C67890",
                timestamp="1234567890.123456",
                team_id="T11111",
            )

    def test_slack_message_requires_channel_id(self):
        """Test SlackMessage requires a channel_id."""
        with pytest.raises(ValueError, match="channel_id is required"):
            SlackMessage(
                text="Test message",
                user_id="U12345",
                channel_id="",
                timestamp="1234567890.123456",
                team_id="T11111",
            )

    def test_slack_message_context_for_ai(self):
        """Test SlackMessage provides context suitable for AI processing."""
        message = SlackMessage(
            text="The deployment failed again 😭",
            user_id="U12345",
            channel_id="C67890",
            timestamp="1234567890.123456",
            team_id="T11111",
        )

        context = message.get_context_for_ai()
        assert "The deployment failed again 😭" in context
        assert len(context) <= 200  # Should be truncated for AI context

    def test_to_dict_round_trip(self) -> None:
        """SlackMessage can be serialized and restored."""
        message = SlackMessage(
            text="round trip",
            user_id="U1",
            channel_id="C1",
            timestamp="1.2",
            team_id="T1",
        )

        data = message.to_dict()
        restored = SlackMessage.from_dict(data)

        assert restored == message
