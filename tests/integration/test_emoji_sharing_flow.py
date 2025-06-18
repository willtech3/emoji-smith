"""Integration tests for emoji sharing flow."""

import pytest
from unittest.mock import AsyncMock
from io import BytesIO
from PIL import Image

from emojismith.application.services.emoji_service import EmojiCreationService
from emojismith.domain.entities.slack_message import SlackMessage
from emojismith.domain.entities.generated_emoji import GeneratedEmoji
from emojismith.infrastructure.slack.slack_file_sharing import (
    SlackFileSharingRepository,
)


@pytest.mark.asyncio
class TestEmojiSharingFlow:
    """Test the complete emoji sharing flow."""

    @pytest.fixture
    def mock_slack_client(self):
        """Create mock Slack client."""
        client = AsyncMock()
        # Mock successful responses
        client.files_upload_v2.return_value = {
            "ok": True,
            "file": {"id": "F123", "url_private": "https://files.slack.com/..."},
        }
        client.chat_postMessage.return_value = {"ok": True, "ts": "1234567890.123456"}
        client.views_open = AsyncMock()
        return client

    @pytest.fixture
    def mock_emoji_generator(self):
        """Create mock emoji generator that returns a valid image."""
        generator = AsyncMock()

        async def generate_mock(spec, name):
            # Create a small test image
            img = Image.new("RGBA", (128, 128), "red")
            buf = BytesIO()
            img.save(buf, format="PNG")
            return GeneratedEmoji(
                name=name, image_data=buf.getvalue()  # Use the provided name
            )

        generator.generate.side_effect = generate_mock
        return generator

    @pytest.fixture
    def emoji_service(self, mock_slack_client, mock_emoji_generator):
        """Create emoji service with mocked dependencies."""
        slack_repo = AsyncMock()
        slack_repo.open_modal = AsyncMock()
        slack_repo.upload_emoji.return_value = False  # Simulate non-Enterprise

        file_sharing_repo = SlackFileSharingRepository(mock_slack_client)

        return EmojiCreationService(
            slack_repo=slack_repo,
            emoji_generator=mock_emoji_generator,
            file_sharing_repo=file_sharing_repo,
        )

    async def test_complete_flow_from_message_action_to_file_share(
        self, emoji_service, mock_slack_client
    ):
        """Test complete flow from message action to file sharing."""
        # 1. User triggers message action
        message = SlackMessage(
            text="Deploy failed again",
            user_id="U123456",
            channel_id="C789012",
            timestamp="1234567890.123456",
            team_id="T111111",
        )
        trigger_id = "12345.98765"

        # 2. Modal opens
        await emoji_service.initiate_emoji_creation(message, trigger_id)
        emoji_service._slack_repo.open_modal.assert_called_once()

        # 3. User submits modal with preferences
        modal_payload = {
            "type": "view_submission",
            "view": {
                "callback_id": "emoji_creation_modal",
                "state": {
                    "values": {
                        "emoji_name": {"name": {"value": "facepalm"}},
                        "emoji_description": {"description": {"value": "facepalm"}},
                        "share_location": {
                            "share_location_select": {
                                "selected_option": {"value": "new_thread"}
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
                "private_metadata": (
                    '{"message_text": "Deploy failed again", '
                    '"user_id": "U123456", "channel_id": "C789012", '
                    '"timestamp": "1234567890.123456", "team_id": "T111111"}'
                ),
            },
        }

        # 4. Process submission (synchronous mode for testing)
        response = await emoji_service.handle_modal_submission(modal_payload)
        assert response["response_action"] == "clear"

        # 5. Verify file was shared
        mock_slack_client.files_upload_v2.assert_called_once()
        upload_args = mock_slack_client.files_upload_v2.call_args[1]
        assert upload_args["filename"] == "facepalm.png"
        assert upload_args["channels"] == ["C789012"]
        assert "upload" in upload_args["initial_comment"].lower()

        # 6. Verify thread was created
        mock_slack_client.chat_postMessage.assert_called_once()
        message_args = mock_slack_client.chat_postMessage.call_args[1]
        assert message_args["channel"] == "C789012"

    async def test_flow_shares_to_existing_thread_when_requested(
        self, emoji_service, mock_slack_client
    ):
        """Test sharing to existing thread when in thread context."""

        # Submit modal choosing to share in thread
        modal_payload = {
            "type": "view_submission",
            "view": {
                "callback_id": "emoji_creation_modal",
                "state": {
                    "values": {
                        "emoji_name": {"name": {"value": "bug"}},
                        "emoji_description": {"description": {"value": "bug"}},
                        "share_location": {
                            "share_location_select": {
                                "selected_option": {"value": "thread"}
                            }
                        },
                        "instruction_visibility": {
                            "visibility_select": {
                                "selected_option": {"value": "hidden"}
                            }
                        },
                        "image_size": {
                            "size_select": {"selected_option": {"value": "1024x1024"}}
                        },
                    }
                },
                "private_metadata": (
                    '{"message_text": "Bug in production", '
                    '"user_id": "U123456", "channel_id": "C789012", '
                    '"timestamp": "1234567890.123456", "team_id": "T111111", '
                    '"thread_ts": "1234567890.123456"}'
                ),
            },
        }

        await emoji_service.handle_modal_submission(modal_payload)

        # Verify file was uploaded to thread
        upload_args = mock_slack_client.files_upload_v2.call_args[1]
        assert upload_args["thread_ts"] == "1234567890.123456"

        # Verify ephemeral message for requester only
        mock_slack_client.chat_postEphemeral.assert_called_once()
        ephemeral_args = mock_slack_client.chat_postEphemeral.call_args[1]
        assert ephemeral_args["user"] == "U123456"
