"""Tests for emoji creation service."""

import pytest
from unittest.mock import AsyncMock
from io import BytesIO
from PIL import Image
from emojismith.application.services.emoji_service import EmojiCreationService
from emojismith.domain.entities.slack_message import SlackMessage
from emojismith.domain.services.generation_service import EmojiGenerationService
from emojismith.domain.entities.generated_emoji import GeneratedEmoji


class TestEmojiCreationService:
    """Test emoji creation service orchestration."""

    @pytest.fixture
    def mock_slack_repo(self):
        """Mock Slack repository."""
        return AsyncMock()

    @pytest.fixture
    def mock_emoji_generator(self):
        return AsyncMock(spec=EmojiGenerationService)

    @pytest.fixture
    def emoji_service(self, mock_slack_repo, mock_emoji_generator):
        """Emoji creation service with mocked dependencies."""
        return EmojiCreationService(
            slack_repo=mock_slack_repo, emoji_generator=mock_emoji_generator
        )

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

    async def test_handle_modal_submission_malformed_payload(self, emoji_service):
        """Test handle_modal_submission raises ValueError on malformed payload."""
        bad_payload = {"view": {"callback_id": "emoji_creation_modal", "state": {}}}
        with pytest.raises(ValueError, match="Malformed modal submission payload"):
            await emoji_service.handle_modal_submission(bad_payload)

    async def test_processes_emoji_generation_job_end_to_end(
        self, emoji_service, mock_slack_repo, mock_emoji_generator
    ):
        """Test complete emoji generation job processing."""
        job_data = {
            "message_text": "The deployment failed again 😭",
            "user_description": "facepalm reaction",
            "user_id": "U12345",
            "channel_id": "C67890",
            "timestamp": "1234567890.123456",
            "team_id": "T11111",
            "emoji_name": "facepalm",
        }

        mock_slack_repo.upload_emoji.return_value = True
        img = Image.new("RGBA", (128, 128), "red")
        buf = BytesIO()
        img.save(buf, format="PNG")
        mock_emoji_generator.generate.return_value = GeneratedEmoji(
            image_data=buf.getvalue(), name="facepalm"
        )

        await emoji_service.process_emoji_generation_job_dict(job_data)

        mock_emoji_generator.generate.assert_called_once()
        mock_slack_repo.upload_emoji.assert_called_once()
        mock_slack_repo.add_emoji_reaction.assert_called_once()
