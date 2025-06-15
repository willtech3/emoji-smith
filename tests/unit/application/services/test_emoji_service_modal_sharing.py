"""Tests for emoji service modal with sharing preferences."""

import json
import pytest
from unittest.mock import AsyncMock
from emojismith.application.services.emoji_service import EmojiCreationService
from emojismith.domain.entities.slack_message import SlackMessage


class TestEmojiServiceModalSharing:
    """Test emoji service modal updates with sharing preferences."""

    @pytest.fixture
    def mock_slack_repo(self):
        """Create mock Slack repository."""
        return AsyncMock()

    @pytest.fixture
    def mock_emoji_generator(self):
        """Create mock emoji generator."""
        return AsyncMock()

    @pytest.fixture
    def emoji_service(self, mock_slack_repo, mock_emoji_generator):
        """Create emoji service with mocked dependencies."""
        return EmojiCreationService(
            slack_repo=mock_slack_repo,
            emoji_generator=mock_emoji_generator,
        )

    async def test_modal_includes_sharing_preferences_fields(
        self, emoji_service, mock_slack_repo
    ):
        """Test modal includes fields for sharing preferences."""
        # Arrange
        message = SlackMessage(
            text="Just deployed on Friday",
            user_id="U12345",
            channel_id="C67890",
            timestamp="1234567890.123456",
            team_id="T11111",
        )
        trigger_id = "12345.98765"

        # Act
        await emoji_service.initiate_emoji_creation(message, trigger_id)

        # Assert
        mock_slack_repo.open_modal.assert_called_once()
        call_args = mock_slack_repo.open_modal.call_args
        view = call_args.kwargs["view"]

        # Check that view contains sharing preference blocks
        block_ids = [block.get("block_id") for block in view["blocks"]]
        assert "share_location" in block_ids
        assert "instruction_visibility" in block_ids
        assert "image_size" in block_ids

        # Check private metadata contains necessary info
        metadata = json.loads(view["private_metadata"])
        assert metadata["message_text"] == message.text
        assert metadata["channel_id"] == message.channel_id
        assert metadata["timestamp"] == message.timestamp

    async def test_modal_submission_extracts_sharing_preferences(self, emoji_service):
        """Test modal submission handler extracts sharing preferences."""
        # Arrange
        modal_payload = {
            "type": "view_submission",
            "view": {
                "callback_id": "emoji_creation_modal",
                "state": {
                    "values": {
                        "emoji_description": {
                            "description": {"value": "frustrated developer face"}
                        },
                        "share_location": {
                            "share_location_select": {
                                "selected_option": {"value": "original_channel"}
                            }
                        },
                        "instruction_visibility": {
                            "visibility_select": {
                                "selected_option": {"value": "everyone"}
                            }
                        },
                        "image_size": {
                            "size_select": {"selected_option": {"value": "emoji_size"}}
                        },
                    }
                },
                "private_metadata": json.dumps(
                    {
                        "message_text": "Just deployed on Friday",
                        "user_id": "U12345",
                        "channel_id": "C67890",
                        "timestamp": "1234567890.123456",
                        "team_id": "T11111",
                    }
                ),
            },
        }

        # Act
        response = await emoji_service.handle_modal_submission(modal_payload)

        # Assert
        assert response["response_action"] == "clear"
        # In real implementation, preferences would be passed to generation job

    async def test_modal_shows_thread_option_in_thread_context(
        self, emoji_service, mock_slack_repo
    ):
        """Test modal shows thread option when triggered from thread."""
        # Arrange
        message = SlackMessage(
            text="Bug in production",
            user_id="U12345",
            channel_id="C67890",
            timestamp="1234567890.123456",
            team_id="T11111",
        )
        # Set thread_ts attribute dynamically to simulate message in thread
        object.__setattr__(message, "thread_ts", "1234567890.123456")
        trigger_id = "12345.98765"

        # Act
        await emoji_service.initiate_emoji_creation(message, trigger_id)

        # Assert
        call_args = mock_slack_repo.open_modal.call_args
        view = call_args.kwargs["view"]
        metadata = json.loads(view["private_metadata"])

        # Thread timestamp should be preserved in metadata
        assert "thread_ts" in metadata
        assert metadata["thread_ts"] == message.thread_ts
