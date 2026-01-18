"""Tests for Slack file sharing repository."""

from io import BytesIO
from unittest.mock import AsyncMock

import pytest
from PIL import Image

from emojismith.domain.dtos import GeneratedEmojiDto
from emojismith.infrastructure.slack.slack_file_sharing import (
    SlackFileSharingRepository,
)
from shared.domain.value_objects import (
    EmojiSharingPreferences,
    ImageSize,
    InstructionVisibility,
    ShareLocation,
)


@pytest.mark.integration()
class TestSlackFileSharingRepository:
    """Test Slack file sharing repository."""

    @pytest.fixture()
    def mock_slack_client(self):
        """Create mock Slack client."""
        return AsyncMock()

    @pytest.fixture()
    def file_sharing_repo(self, mock_slack_client):
        """Create file sharing repository with mock client."""
        return SlackFileSharingRepository(mock_slack_client)

    @pytest.fixture()
    def sample_emoji(self):
        """Create sample emoji with image data."""
        # Create a small test image
        img = Image.new("RGBA", (128, 128), "red")
        buf = BytesIO()
        img.save(buf, format="PNG")
        return GeneratedEmojiDto(name="test_emoji", image_data=buf.getvalue())

    async def test_shares_emoji_file_to_new_thread(
        self, file_sharing_repo, mock_slack_client, sample_emoji
    ):
        """Test sharing emoji file creates new thread."""
        # Arrange
        prefs = EmojiSharingPreferences(
            share_location=ShareLocation.NEW_THREAD,
            instruction_visibility=InstructionVisibility.EVERYONE,
            image_size=ImageSize.EMOJI_SIZE,
        )
        channel_id = "C123456"

        # Mock file upload response
        mock_slack_client.files_upload_v2.return_value = {
            "ok": True,
            "file": {"id": "F123456", "url_private": "https://files.slack.com/..."},
        }

        # Mock thread creation response
        mock_slack_client.chat_postMessage.return_value = {
            "ok": True,
            "ts": "1234567890.123456",
        }

        # Act
        result = await file_sharing_repo.share_emoji_file(
            emoji=sample_emoji,
            channel_id=channel_id,
            preferences=prefs,
            requester_user_id="U789012",
            original_message_ts="1234567890.000111",
            initial_comment="Test comment",
        )

        # Assert
        assert result.success is True
        assert result.thread_ts == "1234567890.123456"
        assert result.file_url == "https://files.slack.com/..."

        # Verify file was uploaded
        mock_slack_client.files_upload_v2.assert_called_once()
        upload_args = mock_slack_client.files_upload_v2.call_args[1]
        assert upload_args["filename"] == "test_emoji.png"
        assert upload_args["channels"] == [channel_id]
        assert upload_args["thread_ts"] == "1234567890.000111"
        assert "initial_comment" not in upload_args

        # Verify instructions were posted
        mock_slack_client.chat_postMessage.assert_called()
        message_args = mock_slack_client.chat_postMessage.call_args[1]
        assert message_args["text"] == "Test comment"

    async def test_shares_emoji_file_to_existing_thread(
        self, file_sharing_repo, mock_slack_client, sample_emoji
    ):
        """Test sharing emoji file to existing thread."""
        # Arrange
        thread_ts = "1234567890.123456"
        prefs = EmojiSharingPreferences(
            share_location=ShareLocation.THREAD,
            instruction_visibility=InstructionVisibility.SUBMITTER_ONLY,
            image_size=ImageSize.EMOJI_SIZE,
            thread_ts=thread_ts,
            include_upload_instructions=True,
        )
        channel_id = "C123456"

        # Mock responses
        mock_slack_client.files_upload_v2.return_value = {
            "ok": True,
            "file": {"id": "F123456", "url_private": "https://files.slack.com/..."},
        }
        mock_slack_client.chat_postEphemeral.return_value = {"ok": True}

        # Act
        result = await file_sharing_repo.share_emoji_file(
            emoji=sample_emoji,
            channel_id=channel_id,
            preferences=prefs,
            requester_user_id="U789012",
            initial_comment="Test comment",
            upload_instructions="Private instructions",
        )

        # Assert
        assert result.success is True
        assert result.thread_ts == thread_ts

        # Verify file was uploaded to thread
        upload_args = mock_slack_client.files_upload_v2.call_args[1]
        assert upload_args["thread_ts"] == thread_ts
        assert upload_args["initial_comment"] == "Test comment"

        # Verify ephemeral message for requester only
        mock_slack_client.chat_postEphemeral.assert_called_once()
        ephemeral_args = mock_slack_client.chat_postEphemeral.call_args[1]
        assert ephemeral_args["user"] == "U789012"
        assert ephemeral_args["channel"] == channel_id
        assert ephemeral_args["text"] == "Private instructions"

    async def test_shares_full_size_image_when_requested(
        self, file_sharing_repo, mock_slack_client
    ):
        """Test sharing full size image when requested."""
        # Arrange
        # Create a larger test image
        img = Image.new("RGBA", (1024, 1024), "blue")
        buf = BytesIO()
        img.save(buf, format="PNG")
        full_size_emoji = GeneratedEmojiDto(name="big_emoji", image_data=buf.getvalue())

        prefs = EmojiSharingPreferences(
            share_location=ShareLocation.NEW_THREAD,
            instruction_visibility=InstructionVisibility.EVERYONE,
            image_size=ImageSize.LARGE,
        )

        mock_slack_client.files_upload_v2.return_value = {
            "ok": True,
            "file": {"id": "F123"},
        }
        mock_slack_client.chat_postMessage.return_value = {"ok": True, "ts": "123.456"}

        # Act
        await file_sharing_repo.share_emoji_file(
            emoji=full_size_emoji,
            channel_id="C123",
            preferences=prefs,
            requester_user_id="U123",
        )

        # Assert
        upload_args = mock_slack_client.files_upload_v2.call_args[1]
        uploaded_data = upload_args["file"]
        assert hasattr(uploaded_data, "read")
        uploaded_data.seek(0)
        data_bytes = uploaded_data.read()
        assert len(data_bytes) > 1000  # Full size image has data

    async def test_includes_upload_instructions_in_message(
        self, file_sharing_repo, mock_slack_client, sample_emoji
    ):
        """Test that upload instructions are included in the message."""
        # Arrange
        prefs = EmojiSharingPreferences(
            share_location=ShareLocation.NEW_THREAD,
            instruction_visibility=InstructionVisibility.EVERYONE,
            image_size=ImageSize.EMOJI_SIZE,
            include_upload_instructions=True,
        )

        mock_slack_client.files_upload_v2.return_value = {
            "ok": True,
            "file": {"id": "F123", "name": "test_emoji.png"},
        }
        mock_slack_client.chat_postMessage.return_value = {"ok": True, "ts": "123.456"}

        # Act
        await file_sharing_repo.share_emoji_file(
            emoji=sample_emoji,
            channel_id="C123",
            preferences=prefs,
            requester_user_id="U123",
            initial_comment="Comment with instructions",
        )

        # Assert - instructions are in the file upload initial comment
        mock_slack_client.files_upload_v2.assert_called_once()
        upload_args = mock_slack_client.files_upload_v2.call_args[1]
        assert upload_args["initial_comment"] == "Comment with instructions"

    async def test_rejects_file_exceeding_size_limit(
        self, file_sharing_repo, mock_slack_client
    ):
        """Test early rejection when image exceeds Slack file size limit."""
        import unittest.mock
        from io import BytesIO

        small_emoji = GeneratedEmojiDto(name="huge", image_data=b"small_data")
        prefs = EmojiSharingPreferences(
            share_location=ShareLocation.NEW_THREAD,
            instruction_visibility=InstructionVisibility.EVERYONE,
            image_size=ImageSize.EMOJI_SIZE,
        )

        oversized_data = BytesIO(b"0" * (9 * 1024 * 1024))  # 9 MiB
        with unittest.mock.patch.object(
            file_sharing_repo, "_prepare_image_data", return_value=oversized_data
        ):
            # Act
            result = await file_sharing_repo.share_emoji_file(
                emoji=small_emoji,
                channel_id="C123",
                preferences=prefs,
                requester_user_id="U123",
            )

        assert result.success is False
        assert result.error == "file_too_large"
        mock_slack_client.files_upload_v2.assert_not_called()

    async def test_handles_file_upload_failure_gracefully(
        self, file_sharing_repo, mock_slack_client, sample_emoji
    ):
        """Test handling of file upload failures."""
        prefs = EmojiSharingPreferences(
            share_location=ShareLocation.NEW_THREAD,
            instruction_visibility=InstructionVisibility.EVERYONE,
            image_size=ImageSize.EMOJI_SIZE,
        )

        mock_slack_client.files_upload_v2.return_value = {
            "ok": False,
            "error": "file_size_too_large",
        }

        # Act
        result = await file_sharing_repo.share_emoji_file(
            emoji=sample_emoji,
            channel_id="C123",
            preferences=prefs,
            requester_user_id="U123",
        )

        assert result.success is False
        assert result.error == "file_size_too_large"
        assert result.file_url is None
