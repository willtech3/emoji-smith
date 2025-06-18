"""Tests for simplified webhook handler (package Lambda)."""

import pytest
from unittest.mock import AsyncMock
from webhook.handler import WebhookHandler


class TestWebhookHandler:
    """Test webhook handler for package Lambda."""

    @pytest.fixture
    def mock_slack_repo(self):
        return AsyncMock()

    @pytest.fixture
    def mock_job_queue(self):
        return AsyncMock()

    @pytest.fixture
    def webhook_handler(self, mock_slack_repo, mock_job_queue):
        return WebhookHandler(slack_repo=mock_slack_repo, job_queue=mock_job_queue)

    async def test_handles_message_action_opens_modal_immediately(
        self, webhook_handler, mock_slack_repo
    ):
        """Test webhook handler opens modal immediately for fast response."""
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
        assert result == {"status": "ok"}
        mock_slack_repo.open_modal.assert_called_once()

    async def test_message_action_accepts_extra_team_fields(
        self, webhook_handler, mock_slack_repo
    ):
        """Team objects may include additional fields beyond the schema."""

        payload = {
            "type": "message_action",
            "callback_id": "create_emoji_reaction",
            "trigger_id": "TRIG",
            "user": {"id": "U2", "name": "testuser"},
            "message": {"text": "extra team", "user": "U1", "ts": "123.456"},
            "channel": {"id": "C1"},
            "team": {"id": "T1", "domain": "example"},
        }

        result = await webhook_handler.handle_message_action(payload)

        assert result == {"status": "ok"}
        mock_slack_repo.open_modal.assert_called_once()

    async def test_handles_modal_submission_queues_emoji_job(
        self, webhook_handler, mock_job_queue
    ):
        """Test modal submission queues emoji generation job."""
        # Arrange
        modal_payload = {
            "type": "view_submission",
            "view": {
                "callback_id": "emoji_creation_modal",
                "state": {
                    "values": {
                        "emoji_description": {"description": {"value": "facepalm"}},
                        "emoji_name": {"name": {"value": "facepalm"}},
                        "share_location": {
                            "share_location_select": {
                                "selected_option": {"value": "channel"}
                            }
                        },
                        "instruction_visibility": {
                            "visibility_select": {
                                "selected_option": {"value": "visible"}
                            }
                        },
                        "image_size": {
                            "size_select": {"selected_option": {"value": "512x512"}}
                        },
                    }
                },
                "private_metadata": (
                    '{"message_text": "test", "user_id": "U123", '
                    '"channel_id": "C123", "timestamp": "123.456", '
                    '"team_id": "T123"}'
                ),
            },
        }

        # Act
        result = await webhook_handler.handle_modal_submission(modal_payload)

        # Assert
        assert result == {"response_action": "clear"}
        mock_job_queue.enqueue_job.assert_called_once()

    async def test_validates_callback_id_in_payload(self, webhook_handler):
        """Test webhook handler validates correct callback ID."""
        # Arrange
        invalid_payload = {
            "type": "message_action",
            "callback_id": "wrong_callback_id",
            "trigger_id": "TRIG",
            "user": {"id": "U2", "name": "testuser"},
            "message": {"text": "test", "user": "U1", "ts": "123.456"},
            "channel": {"id": "C1"},
            "team": {"id": "T1"},
        }

        # Act & Assert
        with pytest.raises(ValueError, match="Invalid callback_id"):
            await webhook_handler.handle_message_action(invalid_payload)

    async def test_handles_slack_api_error_gracefully(
        self, webhook_handler, mock_slack_repo
    ):
        """Test webhook handler handles Slack API errors gracefully."""
        # Arrange
        payload = {
            "type": "message_action",
            "callback_id": "create_emoji_reaction",
            "trigger_id": "TRIG",
            "user": {"id": "U2", "name": "testuser"},
            "message": {"text": "test", "user": "U1", "ts": "123.456"},
            "channel": {"id": "C1"},
            "team": {"id": "T1"},
        }
        mock_slack_repo.open_modal.side_effect = Exception("Slack API error")

        # Act
        result = await webhook_handler.handle_message_action(payload)

        # Assert
        assert result["status"] == "error"
        assert "Failed to create emoji" in result["error"]

    async def test_message_action_accepts_extra_message_fields(
        self, webhook_handler, mock_slack_repo
    ):
        """Message payloads may include additional fields beyond the schema."""

        payload = {
            "type": "message_action",
            "callback_id": "create_emoji_reaction",
            "trigger_id": "TRIG",
            "user": {"id": "U2", "name": "testuser"},
            "message": {
                "text": "extra fields",
                "user": "U1",
                "ts": "123.456",
                "type": "message",
                "client_msg_id": "abc123",
            },
            "channel": {"id": "C1"},
            "team": {"id": "T1"},
        }

        result = await webhook_handler.handle_message_action(payload)

        assert result == {"status": "ok"}
        mock_slack_repo.open_modal.assert_called_once()
