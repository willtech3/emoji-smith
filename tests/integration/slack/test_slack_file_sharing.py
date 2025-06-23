"""Tests for Slack file sharing repository."""

import pytest
from unittest.mock import AsyncMock
from io import BytesIO
from PIL import Image

from emojismith.infrastructure.slack.slack_file_sharing import (
    SlackFileSharingRepository,
)
from emojismith.domain.entities.generated_emoji import GeneratedEmoji
from shared.domain.value_objects import (
    EmojiSharingPreferences,
    ShareLocation,
    InstructionVisibility,
    ImageSize,
)


@pytest.mark.integration
class TestSlackFileSharingRepository:
    """Test Slack file sharing repository."""

    @pytest.fixture
    def mock_slack_client(self):
        """Create mock Slack client."""
        return AsyncMock()

    @pytest.fixture
    def file_sharing_repo(self, mock_slack_client):
        """Create file sharing repository with mock client."""
        return SlackFileSharingRepository(mock_slack_client)

    @pytest.fixture
    def sample_emoji(self):
        """Create sample emoji with image data."""
        # Create a small test image
        img = Image.new("RGBA", (128, 128), "red")
        buf = BytesIO()
        img.save(buf, format="PNG")
        return GeneratedEmoji(name="test_emoji", image_data=buf.getvalue())

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

        # Verify instructions were posted
        mock_slack_client.chat_postMessage.assert_called()

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
        )

        # Assert
        assert result.success is True
        assert result.thread_ts == thread_ts

        # Verify file was uploaded to thread
        upload_args = mock_slack_client.files_upload_v2.call_args[1]
        assert upload_args["thread_ts"] == thread_ts

        # Verify ephemeral message for requester only
        mock_slack_client.chat_postEphemeral.assert_called_once()
        ephemeral_args = mock_slack_client.chat_postEphemeral.call_args[1]
        assert ephemeral_args["user"] == "U789012"
        assert ephemeral_args["channel"] == channel_id

    async def test_shares_full_size_image_when_requested(
        self, file_sharing_repo, mock_slack_client
    ):
        """Test sharing full size image when requested."""
        # Arrange
        # Create a larger test image
        img = Image.new("RGBA", (1024, 1024), "blue")
        buf = BytesIO()
        img.save(buf, format="PNG")
        full_size_emoji = GeneratedEmoji(name="big_emoji", image_data=buf.getvalue())

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
        # Should upload the full size image without resizing
        uploaded_data = upload_args["file"]
        # Check that it's a BytesIO object with data
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
        )

        # Assert - instructions are in the file upload initial comment
        upload_args = mock_slack_client.files_upload_v2.call_args[1]
        initial_comment = upload_args["initial_comment"].lower()
        assert all(
            term in initial_comment for term in ["test_emoji", "upload", "workspace"]
        )

    async def test_rejects_file_exceeding_size_limit(
        self, file_sharing_repo, mock_slack_client
    ):
        """Test early rejection when image exceeds Slack file size limit."""
        # Arrange – We can't create a GeneratedEmoji larger than 64KB due to
        # domain constraints, so we'll test this by mocking the
        # _prepare_image_data method to return large data
        import unittest.mock
        from io import BytesIO

        # Create normal emoji first
        small_emoji = GeneratedEmoji(name="huge", image_data=b"small_data")
        prefs = EmojiSharingPreferences(
            share_location=ShareLocation.NEW_THREAD,
            instruction_visibility=InstructionVisibility.EVERYONE,
            image_size=ImageSize.EMOJI_SIZE,
        )

        # Mock _prepare_image_data to return oversized data
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

        # Assert – should fail fast before Slack API call
        assert result.success is False
        assert result.error == "file_too_large"
        mock_slack_client.files_upload_v2.assert_not_called()

    async def test_handles_file_upload_failure_gracefully(
        self, file_sharing_repo, mock_slack_client, sample_emoji
    ):
        """Test handling of file upload failures."""
        # Arrange
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

        # Assert
        assert result.success is False
        assert result.error == "file_size_too_large"
        assert result.file_url is None

    async def test_no_duplicate_emoji_messages_for_new_thread(
        self, file_sharing_repo, mock_slack_client, sample_emoji
    ):
        """Test that new thread creation doesn't produce duplicate emoji messages."""
        # Arrange
        prefs = EmojiSharingPreferences(
            share_location=ShareLocation.NEW_THREAD,
            instruction_visibility=InstructionVisibility.EVERYONE,
            image_size=ImageSize.EMOJI_SIZE,
            include_upload_instructions=True,
        )
        channel_id = "C123456"
        original_message_ts = "1234567890.000111"

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
            original_message_ts=original_message_ts,
        )

        # Assert
        assert result.success is True

        # Verify file upload was called once
        mock_slack_client.files_upload_v2.assert_called_once()
        upload_args = mock_slack_client.files_upload_v2.call_args[1]

        # For new thread: file upload should NOT have initial_comment
        # (to avoid duplicate with the separate thread message)
        assert "initial_comment" not in upload_args

        # Verify exactly one thread message was posted
        mock_slack_client.chat_postMessage.assert_called_once()
        message_args = mock_slack_client.chat_postMessage.call_args[1]

        # Thread message should contain the emoji name and instructions
        message_text = message_args["text"]
        assert "Generated custom emoji: :test_emoji:" in message_text
        assert "workspace" in message_text.lower()  # Instructions included
        assert message_args["thread_ts"] == original_message_ts

        # Verify no additional ephemeral messages for EVERYONE visibility
        mock_slack_client.chat_postEphemeral.assert_not_called()

    async def test_existing_thread_uses_initial_comment_not_separate_message(
        self, file_sharing_repo, mock_slack_client, sample_emoji
    ):
        """Test existing thread sharing uses initial_comment, not separate message."""
        # Arrange
        thread_ts = "1234567890.123456"
        prefs = EmojiSharingPreferences(
            share_location=ShareLocation.THREAD,
            instruction_visibility=InstructionVisibility.EVERYONE,
            image_size=ImageSize.EMOJI_SIZE,
            include_upload_instructions=True,
            thread_ts=thread_ts,
        )
        channel_id = "C123456"

        # Mock file upload response
        mock_slack_client.files_upload_v2.return_value = {
            "ok": True,
            "file": {"id": "F123456", "url_private": "https://files.slack.com/..."},
        }

        # Act
        result = await file_sharing_repo.share_emoji_file(
            emoji=sample_emoji,
            channel_id=channel_id,
            preferences=prefs,
            requester_user_id="U789012",
        )

        # Assert
        assert result.success is True

        # Verify file upload was called with initial_comment
        upload_args = mock_slack_client.files_upload_v2.call_args[1]
        assert "initial_comment" in upload_args

        initial_comment = upload_args["initial_comment"]
        assert "Generated custom emoji: :test_emoji:" in initial_comment
        assert "workspace" in initial_comment.lower()  # Instructions included

        # Verify NO separate thread message was posted for existing thread
        mock_slack_client.chat_postMessage.assert_not_called()

        # Verify no additional ephemeral messages for EVERYONE visibility
        mock_slack_client.chat_postEphemeral.assert_not_called()

    async def test_upload_instructions_consistent_across_visibility_settings(
        self, file_sharing_repo, mock_slack_client, sample_emoji
    ):
        """Ensure upload instructions are consistent across visibility settings."""
        # Test with EVERYONE visibility (instructions in file comment)
        prefs_everyone = EmojiSharingPreferences(
            share_location=ShareLocation.ORIGINAL_CHANNEL,
            instruction_visibility=InstructionVisibility.EVERYONE,
            image_size=ImageSize.EMOJI_SIZE,
            include_upload_instructions=True,
        )

        mock_slack_client.files_upload_v2.return_value = {
            "ok": True,
            "file": {"url_private": "https://files.slack.com/test.png"},
        }

        await file_sharing_repo.share_emoji_file(
            emoji=sample_emoji,
            channel_id="C123456",
            preferences=prefs_everyone,
            requester_user_id="U789",
        )

        # Capture the initial comment from the file upload
        upload_call = mock_slack_client.files_upload_v2.call_args
        initial_comment = upload_call.kwargs.get("initial_comment", "")

        # Test with SUBMITTER_ONLY visibility (instructions in ephemeral message)
        prefs_submitter = EmojiSharingPreferences(
            share_location=ShareLocation.ORIGINAL_CHANNEL,
            instruction_visibility=InstructionVisibility.SUBMITTER_ONLY,
            image_size=ImageSize.EMOJI_SIZE,
            include_upload_instructions=True,
        )

        mock_slack_client.reset_mock()
        mock_slack_client.files_upload_v2.return_value = {
            "ok": True,
            "file": {"url_private": "https://files.slack.com/test.png"},
        }

        await file_sharing_repo.share_emoji_file(
            emoji=sample_emoji,
            channel_id="C123456",
            preferences=prefs_submitter,
            requester_user_id="U789",
        )

        # Capture the ephemeral message text
        ephemeral_call = mock_slack_client.chat_postEphemeral.call_args
        ephemeral_text = ephemeral_call.kwargs.get("text", "")

        # Both should contain the same upload steps
        # Check for key instruction elements that should be consistent
        assert "Right-click" in initial_comment
        assert "Right-click" in ephemeral_text
        assert "Add emoji" in initial_comment
        assert "Add emoji" in ephemeral_text
        assert sample_emoji.name in initial_comment
        assert sample_emoji.name in ephemeral_text
