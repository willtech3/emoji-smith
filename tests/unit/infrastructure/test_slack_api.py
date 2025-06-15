"""Tests for Slack API infrastructure implementation."""

import pytest
from unittest.mock import AsyncMock
from emojismith.infrastructure.slack.slack_api import SlackAPIRepository


class TestSlackAPIRepository:
    """Test Slack API repository implementation."""

    @pytest.fixture
    def mock_slack_client(self):
        """Mock Slack WebClient."""
        return AsyncMock()

    @pytest.fixture
    def slack_repo(self, mock_slack_client):
        """Slack repository with mocked client."""
        return SlackAPIRepository(slack_client=mock_slack_client)

    async def test_displays_emoji_creation_dialog_to_user(
        self, slack_repo, mock_slack_client
    ):
        """Test opening modal dialog calls Slack API correctly."""
        # Arrange
        trigger_id = "123456789.987654321.abcdefghijklmnopqrstuvwxyz"
        view = {
            "type": "modal",
            "callback_id": "emoji_creation_modal",
            "title": {"type": "plain_text", "text": "Create Emoji"},
        }
        mock_slack_client.views_open.return_value = {"ok": True}

        # Act
        await slack_repo.open_modal(trigger_id=trigger_id, view=view)

        # Assert
        mock_slack_client.views_open.assert_called_once_with(
            trigger_id=trigger_id, view=view
        )

    async def test_reports_error_when_modal_cannot_be_displayed(
        self, slack_repo, mock_slack_client
    ):
        """Test error handling when Slack API fails."""
        # Arrange
        trigger_id = "123456789.987654321.abcdefghijklmnopqrstuvwxyz"
        view = {"type": "modal"}
        mock_slack_client.views_open.side_effect = Exception("Slack API error")

        # Act & Assert
        with pytest.raises(Exception, match="Slack API error"):
            await slack_repo.open_modal(trigger_id=trigger_id, view=view)

    async def test_adds_custom_emoji_to_workspace(self, slack_repo, mock_slack_client):
        """Test uploading emoji to Slack workspace."""
        # Arrange
        emoji_name = "custom_facepalm"
        emoji_data = b"fake_png_data"
        mock_slack_client.admin_emoji_add.return_value = {"ok": True}

        # Act
        result = await slack_repo.upload_emoji(name=emoji_name, image_data=emoji_data)

        # Assert
        assert result is True
        mock_slack_client.admin_emoji_add.assert_called_once_with(
            name=emoji_name, url="", image=emoji_data
        )

    async def test_applies_emoji_reaction_to_original_message(
        self, slack_repo, mock_slack_client
    ):
        """Test adding emoji reaction to a message."""
        # Arrange
        emoji_name = "custom_facepalm"
        channel_id = "C67890"
        timestamp = "1234567890.123456"
        mock_slack_client.reactions_add.return_value = {"ok": True}

        # Act
        await slack_repo.add_emoji_reaction(
            emoji_name=emoji_name, channel_id=channel_id, timestamp=timestamp
        )

        # Assert
        mock_slack_client.reactions_add.assert_called_once_with(
            name=emoji_name, channel=channel_id, timestamp=timestamp
        )
