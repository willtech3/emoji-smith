"""Tests for Slack webhook handler."""

import pytest
from unittest.mock import AsyncMock
from emojismith.application.handlers.slack_webhook import SlackWebhookHandler


class TestSlackWebhookHandler:
    """Test Slack webhook handler."""

    @pytest.fixture
    def mock_emoji_service(self):
        return AsyncMock()

    @pytest.fixture
    def webhook_handler(self, mock_emoji_service):
        return SlackWebhookHandler(emoji_service=mock_emoji_service)

    async def test_handles_message_action_payload(
        self, webhook_handler, mock_emoji_service
    ):
        """Test webhook handler processes message action payload."""
        # Arrange
        payload = {
            "type": "message_action",
            "callback_id": "create_emoji_reaction",
            "trigger_id": "123456789.987654321.abcdefghijklmnopqrstuvwxyz",
            "user": {"id": "U12345", "name": "testuser"},
            "channel": {"id": "C67890", "name": "general"},
            "message": {
                "text": "Just deployed on Friday afternoon!",
                "ts": "1234567890.123456",
                "user": "U98765",
            },
            "team": {"id": "T11111"},
        }

        # Act
        result = await webhook_handler.handle_message_action(payload)

        # Assert
        assert result is not None
        mock_emoji_service.queue_modal_opening.assert_called_once()

    async def test_handles_message_action_payload_fallback_to_sync(
        self, webhook_handler, mock_emoji_service
    ):
        """Test webhook handler falls back to sync modal opening if queue fails."""
        # Arrange
        payload = {
            "type": "message_action",
            "callback_id": "create_emoji_reaction",
            "trigger_id": "123456789.987654321.abcdefghijklmnopqrstuvwxyz",
            "user": {"id": "U12345", "name": "testuser"},
            "channel": {"id": "C67890", "name": "general"},
            "message": {
                "text": "Just deployed on Friday afternoon!",
                "ts": "1234567890.123456",
                "user": "U98765",
            },
            "team": {"id": "T11111"},
        }

        # Mock queue_modal_opening to fail, should fallback to sync
        mock_emoji_service.queue_modal_opening.side_effect = ValueError(
            "Job queue not configured"
        )

        # Act
        result = await webhook_handler.handle_message_action(payload)

        # Assert
        assert result is not None
        mock_emoji_service.queue_modal_opening.assert_called_once()
        mock_emoji_service.initiate_emoji_creation.assert_called_once()

    async def test_handles_modal_submission_payload(
        self, webhook_handler, mock_emoji_service
    ):
        """Test webhook handler processes modal submission payload."""
        # Arrange
        modal_payload = {
            "type": "view_submission",
            "view": {
                "callback_id": "emoji_creation_modal",
                "state": {
                    "values": {
                        "emoji_description": {"description": {"value": "facepalm"}}
                    }
                },
                "private_metadata": '{"message_text": "test", "user_id": "U123"}',
            },
        }
        mock_emoji_service.handle_modal_submission.return_value = {
            "response_action": "clear"
        }

        # Act
        result = await webhook_handler.handle_modal_submission(modal_payload)

        # Assert
        assert result["response_action"] == "clear"
        mock_emoji_service.handle_modal_submission.assert_called_once_with(
            modal_payload
        )

    async def test_validates_callback_id_in_payload(self, webhook_handler):
        """Test webhook handler validates correct callback ID."""
        # Arrange
        invalid_payload = {
            "type": "message_action",
            "callback_id": "wrong_callback_id",
        }

        # Act & Assert
        with pytest.raises(ValueError, match="Invalid callback_id"):
            await webhook_handler.handle_message_action(invalid_payload)

    async def test_extracts_slack_message_from_payload(
        self, webhook_handler, mock_emoji_service
    ):
        """Test webhook handler correctly extracts SlackMessage from payload."""
        # Arrange
        payload = {
            "type": "message_action",
            "callback_id": "create_emoji_reaction",
            "trigger_id": "123456789.987654321.abcdefghijklmnopqrstuvwxyz",
            "user": {"id": "U12345"},
            "channel": {"id": "C67890"},
            "message": {
                "text": "The deployment failed again 😭",
                "ts": "1234567890.123456",
                "user": "U98765",
            },
            "team": {"id": "T11111"},
        }

        # Act
        await webhook_handler.handle_message_action(payload)

        # Assert
        mock_emoji_service.initiate_emoji_creation.assert_called_once()
        call_args = mock_emoji_service.initiate_emoji_creation.call_args[0]
        slack_message = call_args[0]

        assert slack_message.text == "The deployment failed again 😭"
        assert slack_message.user_id == "U98765"  # Original message author
        assert slack_message.channel_id == "C67890"
        assert slack_message.timestamp == "1234567890.123456"
        assert slack_message.team_id == "T11111"

    async def test_validates_modal_submission_callback_id(self, webhook_handler):
        """Test webhook handler validates modal submission callback ID."""
        # Arrange
        invalid_modal_payload = {
            "type": "view_submission",
            "view": {"callback_id": "wrong_callback_id"},
        }

        # Act & Assert
        with pytest.raises(
            ValueError, match="Invalid callback_id for modal submission"
        ):
            await webhook_handler.handle_modal_submission(invalid_modal_payload)

    async def test_handle_message_action_exception(
        self, webhook_handler, mock_emoji_service
    ):
        """If the emoji service raises, the handler returns an error response."""
        # Arrange
        payload = {
            "type": "message_action",
            "callback_id": "create_emoji_reaction",
            "message": {"text": "test", "user": "U1", "ts": "123.456"},
            "channel": {"id": "C1"},
            "team": {"id": "T1"},
            "trigger_id": "TRIG",
        }
        mock_emoji_service.initiate_emoji_creation.side_effect = Exception("boom")

        # Act
        result = await webhook_handler.handle_message_action(payload)

        # Assert
        assert result["status"] == "error"
        assert "Failed to create emoji" in result["error"]

    async def test_handle_message_action_invalid_callback(self, webhook_handler):
        """Test invalid callback_id for message action raises ValueError."""
        payload = {
            "type": "message_action",
            "callback_id": "wrong",
            "message": {},
            "channel": {"id": "C"},
            "team": {"id": "T"},
            "trigger_id": "TRIG",
        }
        with pytest.raises(ValueError, match="Invalid callback_id"):
            await webhook_handler.handle_message_action(payload)

    async def test_handle_modal_submission_exception(
        self, webhook_handler, mock_emoji_service
    ):
        """If handle_modal_submission raises, the handler returns an error response."""
        # Arrange
        modal_payload = {
            "type": "view_submission",
            "view": {"callback_id": "emoji_creation_modal", "state": {"values": {}}},
        }
        mock_emoji_service.handle_modal_submission.side_effect = Exception("boom")

        # Act
        result = await webhook_handler.handle_modal_submission(modal_payload)

        # Assert
        assert result["status"] == "error"
        assert "internal error" in result["error"].lower()
