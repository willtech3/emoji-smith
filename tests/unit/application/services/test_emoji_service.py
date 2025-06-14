"""Tests for emoji creation service."""

import pytest
from unittest.mock import AsyncMock
from emojismith.application.services.emoji_service import EmojiCreationService
from emojismith.domain.entities.slack_message import SlackMessage


class TestEmojiCreationService:
    """Test emoji creation service orchestration."""

    @pytest.fixture
    def mock_slack_repo(self):
        """Mock Slack repository."""
        return AsyncMock()

    @pytest.fixture
    def emoji_service(self, mock_slack_repo):
        """Emoji creation service with mocked dependencies."""
        return EmojiCreationService(slack_repo=mock_slack_repo)

    async def test_initiates_emoji_creation_opens_modal(
        self, emoji_service, mock_slack_repo
    ):
        """Test initiate emoji creation opens modal dialog."""
        # Arrange
        slack_message = SlackMessage(
            text="Just deployed on Friday afternoon!",
            user_id="U12345",
            channel_id="C67890",
            timestamp="1234567890.123456",
            team_id="T11111",
        )
        trigger_id = "123456789.987654321.abcdefghijklmnopqrstuvwxyz"

        # Act
        await emoji_service.initiate_emoji_creation(slack_message, trigger_id)

        # Assert
        mock_slack_repo.open_modal.assert_called_once()
        call_args = mock_slack_repo.open_modal.call_args
        assert call_args[1]["trigger_id"] == trigger_id

        # Verify modal contains message context
        view = call_args[1]["view"]
        assert view["type"] == "modal"
        assert view["callback_id"] == "emoji_creation_modal"
        assert "Friday afternoon" in str(view)

    async def test_handles_modal_submission_queues_generation_job(
        self, emoji_service, mock_slack_repo
    ):
        """Test modal submission handler queues emoji generation job."""
        # Arrange
        modal_payload = {
            "type": "view_submission",
            "view": {
                "callback_id": "emoji_creation_modal",
                "state": {
                    "values": {
                        "emoji_description": {
                            "description": {"value": "frustrated developer face"}
                        }
                    }
                },
                "private_metadata": (
                    '{"message_text": "Just deployed on Friday", '
                    '"user_id": "U12345", "channel_id": "C67890", '
                    '"timestamp": "1234567890.123456", "team_id": "T11111"}'
                ),
            },
        }

        # Act
        response = await emoji_service.handle_modal_submission(modal_payload)

        # Assert
        assert response["response_action"] == "clear"
        # In real implementation, this would queue a background job

    async def test_processes_emoji_generation_job_end_to_end(
        self, emoji_service, mock_slack_repo
    ):
        """Test complete emoji generation job processing."""
        # Arrange
        job_data = {
            "message_text": "The deployment failed again 😭",
            "user_description": "facepalm reaction",
            "user_id": "U12345",
            "channel_id": "C67890",
            "timestamp": "1234567890.123456",
            "team_id": "T11111",
        }

        # Mock successful emoji upload and reaction
        mock_slack_repo.upload_emoji.return_value = True

        # Act
        await emoji_service.process_emoji_generation_job(job_data)

        # Assert
        # In real implementation, this would:
        # 1. Generate emoji using AI service
        # 2. Upload emoji to Slack workspace
        # 3. Add reaction to original message
        # For now, just verify the method completes without error
