"""Tests for emoji creation service."""

import pytest
from unittest.mock import AsyncMock
from io import BytesIO
from PIL import Image
from emojismith.application.services.emoji_service import EmojiCreationService
from emojismith.domain.entities.generated_emoji import GeneratedEmoji
from emojismith.domain.services.generation_service import EmojiGenerationService


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
    def mock_job_queue(self):
        """Mock job queue repository."""
        return AsyncMock()

    @pytest.fixture
    def mock_file_sharing_repo(self):
        """Mock file sharing repository."""
        return AsyncMock()

    @pytest.fixture
    def emoji_service(
        self, mock_slack_repo, mock_emoji_generator, mock_file_sharing_repo
    ):
        """Emoji creation service with mocked dependencies."""
        return EmojiCreationService(
            slack_repo=mock_slack_repo,
            emoji_generator=mock_emoji_generator,
            file_sharing_repo=mock_file_sharing_repo,
        )

    @pytest.fixture
    def emoji_service_with_queue(
        self,
        mock_slack_repo,
        mock_emoji_generator,
        mock_job_queue,
        mock_file_sharing_repo,
    ):
        """Emoji creation service with job queue enabled."""
        return EmojiCreationService(
            slack_repo=mock_slack_repo,
            emoji_generator=mock_emoji_generator,
            job_queue=mock_job_queue,
            file_sharing_repo=mock_file_sharing_repo,
        )

    async def test_processes_emoji_generation_job_end_to_end(
        self,
        emoji_service,
        mock_slack_repo,
        mock_emoji_generator,
        mock_file_sharing_repo,
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

        # Mock successful file sharing for standard workspace
        from emojismith.infrastructure.slack.slack_file_sharing import FileSharingResult

        mock_file_sharing_repo.share_emoji_file.return_value = FileSharingResult(
            success=True,
            thread_ts="1234567890.123456",
            file_url="https://files.slack.com/test",
        )

        img = Image.new("RGBA", (128, 128), "red")
        buf = BytesIO()
        img.save(buf, format="PNG")
        mock_emoji_generator.generate.return_value = GeneratedEmoji(
            image_data=buf.getvalue(), name="facepalm"
        )

        await emoji_service.process_emoji_generation_job_dict(job_data)

        mock_emoji_generator.generate.assert_called_once()
        # For standard workspace, should use file sharing instead of direct upload
        mock_file_sharing_repo.share_emoji_file.assert_called_once()
        mock_slack_repo.upload_emoji.assert_not_called()

    async def test_processes_emoji_generation_job_entity(
        self,
        emoji_service,
        mock_slack_repo,
        mock_emoji_generator,
        mock_file_sharing_repo,
    ):
        """Test processing emoji generation job from job entity."""
        # Arrange
        from shared.domain.entities import EmojiGenerationJob
        from shared.domain.value_objects import EmojiSharingPreferences
        from emojismith.domain.entities.generated_emoji import GeneratedEmoji
        from emojismith.infrastructure.slack.slack_file_sharing import FileSharingResult
        from io import BytesIO
        from PIL import Image

        job = EmojiGenerationJob.create_new(
            message_text="The deployment failed again 😭",
            user_description="facepalm reaction",
            emoji_name="facepalm_reaction",
            user_id="U12345",
            channel_id="C67890",
            timestamp="1234567890.123456",
            team_id="T11111",
            sharing_preferences=EmojiSharingPreferences.default_for_context(),
        )

        # Mock successful file sharing for standard workspace
        mock_file_sharing_repo.share_emoji_file.return_value = FileSharingResult(
            success=True,
            thread_ts="1234567890.123456",
            file_url="https://files.slack.com/test",
        )

        img = Image.new("RGBA", (128, 128), "red")
        buf = BytesIO()
        img.save(buf, format="PNG")
        mock_emoji_generator.generate.return_value = GeneratedEmoji(
            image_data=buf.getvalue(), name="facepalm_reaction"
        )

        # Act
        await emoji_service.process_emoji_generation_job(job)

        # Assert
        mock_emoji_generator.generate.assert_called_once()
        # For standard workspace, should use file sharing instead of direct upload
        mock_file_sharing_repo.share_emoji_file.assert_called_once()
        mock_slack_repo.upload_emoji.assert_not_called()

        # Verify the call arguments
        generate_call = mock_emoji_generator.generate.call_args
        assert generate_call[0][0].description == "facepalm reaction"
        assert generate_call[0][0].context == "The deployment failed again 😭"

    async def test_process_emoji_generation_job_upload_failure(
        self,
        emoji_service,
        mock_slack_repo,
        mock_emoji_generator,
        mock_file_sharing_repo,
        caplog,
    ):
        """Test processing emoji generation job when file sharing fails gracefully."""
        # Arrange
        from shared.domain.entities import EmojiGenerationJob
        from shared.domain.value_objects import EmojiSharingPreferences
        from emojismith.domain.entities.generated_emoji import GeneratedEmoji
        from emojismith.infrastructure.slack.slack_file_sharing import FileSharingResult
        from io import BytesIO
        from PIL import Image

        job = EmojiGenerationJob.create_new(
            message_text="Test message",
            user_description="test emoji",
            emoji_name="test_emoji",
            user_id="U12345",
            channel_id="C67890",
            timestamp="1234567890.123456",
            team_id="T11111",
            sharing_preferences=EmojiSharingPreferences.default_for_context(),
        )

        # Mock file sharing failure for standard workspace
        mock_file_sharing_repo.share_emoji_file.return_value = FileSharingResult(
            success=False, error="file_size_too_large"
        )

        img = Image.new("RGBA", (128, 128), "red")
        buf = BytesIO()
        img.save(buf, format="PNG")
        mock_emoji_generator.generate.return_value = GeneratedEmoji(
            image_data=buf.getvalue(), name="test_emoji"
        )

        # Act - should complete gracefully, not raise exception
        await emoji_service.process_emoji_generation_job(job)

        # Assert - should log error about file sharing failure
        assert "Failed to share emoji file" in caplog.text
        mock_file_sharing_repo.share_emoji_file.assert_called_once()
        # No direct upload attempted for standard workspace
        mock_slack_repo.upload_emoji.assert_not_called()

    async def test_process_emoji_generation_job_dict_upload_failure(
        self,
        emoji_service,
        mock_slack_repo,
        mock_emoji_generator,
        mock_file_sharing_repo,
        caplog,
    ):
        """Test processing emoji generation job dict when sharing fails."""
        # Arrange
        from emojismith.domain.entities.generated_emoji import GeneratedEmoji
        from emojismith.infrastructure.slack.slack_file_sharing import FileSharingResult
        from io import BytesIO
        from PIL import Image

        job_data = {
            "message_text": "Test message",
            "user_description": "test emoji",
            "emoji_name": "test_emoji",
            "user_id": "U12345",
            "channel_id": "C67890",
            "timestamp": "1234567890.123456",
            "team_id": "T11111",
        }

        # Mock file sharing failure for standard workspace
        mock_file_sharing_repo.share_emoji_file.return_value = FileSharingResult(
            success=False, error="file_size_too_large"
        )

        img = Image.new("RGBA", (128, 128), "red")
        buf = BytesIO()
        img.save(buf, format="PNG")
        mock_emoji_generator.generate.return_value = GeneratedEmoji(
            image_data=buf.getvalue(), name="test_emoji"
        )

        # Act - should complete gracefully, not raise exception
        await emoji_service.process_emoji_generation_job_dict(job_data)

        # Assert - should log error about file sharing failure
        assert "Failed to share emoji file" in caplog.text
        mock_file_sharing_repo.share_emoji_file.assert_called_once()
        # No direct upload attempted for standard workspace
        mock_slack_repo.upload_emoji.assert_not_called()
