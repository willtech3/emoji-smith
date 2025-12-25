"""Tests for emoji creation service."""

from io import BytesIO
from unittest.mock import AsyncMock, MagicMock

import pytest
from PIL import Image

from emojismith.application.services.emoji_service import EmojiCreationService
from emojismith.domain.entities.generated_emoji import GeneratedEmoji


@pytest.mark.unit()
class TestEmojiCreationService:
    """Test emoji creation service orchestration."""

    @pytest.fixture()
    def mock_slack_repo(self):
        """Mock Slack repository."""
        return AsyncMock()

    @pytest.fixture()
    def mock_image_generator(self):
        """Mock image generator (created by factory)."""
        return AsyncMock()

    @pytest.fixture()
    def mock_image_generator_factory(self, mock_image_generator):
        """Mock factory that creates image generators."""
        factory = MagicMock()
        factory.create.return_value = mock_image_generator
        return factory

    @pytest.fixture()
    def mock_image_processor(self):
        """Mock image processor."""
        processor = MagicMock()
        # Return the same data (no-op processing)
        processor.resize_for_emoji.side_effect = lambda data: data
        return processor

    @pytest.fixture()
    def mock_emoji_validator(self):
        """Mock emoji validator."""
        validator = MagicMock()
        # Validator returns the emoji as-is
        validator.validate_and_create.side_effect = lambda data, name: GeneratedEmoji(
            image_data=data, name=name
        )
        return validator

    @pytest.fixture()
    def mock_style_template_manager(self):
        """Mock style template manager."""
        return MagicMock()

    @pytest.fixture()
    def mock_job_queue(self):
        """Mock job queue repository."""
        return AsyncMock()

    @pytest.fixture()
    def mock_file_sharing_repo(self):
        """Mock file sharing repository."""
        return AsyncMock()

    @pytest.fixture()
    def mock_build_prompt_use_case(self):
        """Mock build prompt use case."""
        mock = AsyncMock()
        mock.build_prompt.return_value = "a happy face emoji in cartoon style"
        return mock

    @pytest.fixture()
    def emoji_service(
        self,
        mock_slack_repo,
        mock_image_generator_factory,
        mock_image_processor,
        mock_emoji_validator,
        mock_style_template_manager,
        mock_build_prompt_use_case,
        mock_file_sharing_repo,
    ):
        """Emoji creation service with mocked dependencies."""
        return EmojiCreationService(
            slack_repo=mock_slack_repo,
            build_prompt_use_case=mock_build_prompt_use_case,
            image_generator_factory=mock_image_generator_factory,
            image_processor=mock_image_processor,
            emoji_validator=mock_emoji_validator,
            style_template_manager=mock_style_template_manager,
            file_sharing_repo=mock_file_sharing_repo,
        )

    async def test_processes_emoji_generation_job_end_to_end(
        self,
        emoji_service,
        mock_slack_repo,
        mock_image_generator,
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
        # Return a list of images for multi-image support
        mock_image_generator.generate_image.return_value = [buf.getvalue()]

        await emoji_service.process_emoji_generation_job_dict(job_data)

        mock_image_generator.generate_image.assert_called_once()
        # For standard workspace, should use file sharing instead of direct upload
        mock_file_sharing_repo.share_emoji_file.assert_called_once()
        mock_slack_repo.upload_emoji.assert_not_called()

    async def test_processes_emoji_generation_job_entity(
        self,
        emoji_service,
        mock_slack_repo,
        mock_image_generator,
        mock_file_sharing_repo,
    ):
        """Test processing emoji generation job from job entity."""
        # Arrange
        from io import BytesIO

        from PIL import Image

        from emojismith.infrastructure.slack.slack_file_sharing import FileSharingResult
        from shared.domain.entities import EmojiGenerationJob
        from shared.domain.value_objects import EmojiSharingPreferences

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
        # Return a list of images for multi-image support
        mock_image_generator.generate_image.return_value = [buf.getvalue()]

        # Act
        await emoji_service.process_emoji_generation_job(job)

        # Assert
        mock_image_generator.generate_image.assert_called_once()
        # For standard workspace, should use file sharing instead of direct upload
        mock_file_sharing_repo.share_emoji_file.assert_called_once()
        mock_slack_repo.upload_emoji.assert_not_called()

    async def test_process_emoji_generation_job_upload_failure(
        self,
        emoji_service,
        mock_slack_repo,
        mock_image_generator,
        mock_file_sharing_repo,
        caplog,
    ):
        """Test processing emoji generation job when file sharing fails gracefully."""
        # Arrange
        from io import BytesIO

        from PIL import Image

        from emojismith.infrastructure.slack.slack_file_sharing import FileSharingResult
        from shared.domain.entities import EmojiGenerationJob
        from shared.domain.value_objects import EmojiSharingPreferences

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
        # Return a list of images for multi-image support
        mock_image_generator.generate_image.return_value = [buf.getvalue()]

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
        mock_image_generator,
        mock_file_sharing_repo,
        caplog,
    ):
        """Test processing emoji generation job dict when sharing fails."""
        # Arrange
        from io import BytesIO

        from PIL import Image

        from emojismith.infrastructure.slack.slack_file_sharing import FileSharingResult

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
        # Return a list of images for multi-image support
        mock_image_generator.generate_image.return_value = [buf.getvalue()]

        # Act - should complete gracefully, not raise exception
        await emoji_service.process_emoji_generation_job_dict(job_data)

        # Assert - should log error about file sharing failure
        assert "Failed to share emoji file" in caplog.text
        mock_file_sharing_repo.share_emoji_file.assert_called_once()
        # No direct upload attempted for standard workspace
        mock_slack_repo.upload_emoji.assert_not_called()

    async def test_multi_image_sharing_includes_upload_instructions_only_once(
        self,
        emoji_service,
        mock_image_generator,
        mock_file_sharing_repo,
    ):
        """When multiple emojis are generated, only include upload steps once."""
        from emojismith.infrastructure.slack.slack_file_sharing import FileSharingResult
        from shared.domain.entities import EmojiGenerationJob
        from shared.domain.value_objects import (
            EmojiGenerationPreferences,
            EmojiSharingPreferences,
            NumberOfImages,
        )

        job = EmojiGenerationJob.create_new(
            message_text="The deployment failed again 😭",
            user_description="facepalm reaction",
            emoji_name="facepalm_reaction",
            user_id="U12345",
            channel_id="C67890",
            timestamp="1234567890.123456",
            team_id="T11111",
            sharing_preferences=EmojiSharingPreferences.default_for_context(),
            generation_preferences=EmojiGenerationPreferences(num_images=NumberOfImages.TWO),
        )

        mock_file_sharing_repo.share_emoji_file.side_effect = [
            FileSharingResult(
                success=True,
                thread_ts="1234567890.123456",
                file_url="https://files.slack.com/test1",
            ),
            FileSharingResult(
                success=True,
                thread_ts="1234567890.123456",
                file_url="https://files.slack.com/test2",
            ),
        ]

        img1 = Image.new("RGBA", (128, 128), "red")
        buf1 = BytesIO()
        img1.save(buf1, format="PNG")
        img2 = Image.new("RGBA", (128, 128), "blue")
        buf2 = BytesIO()
        img2.save(buf2, format="PNG")
        mock_image_generator.generate_image.return_value = [buf1.getvalue(), buf2.getvalue()]

        await emoji_service.process_emoji_generation_job(job)

        assert mock_file_sharing_repo.share_emoji_file.call_count == 2
        first_preferences = (
            mock_file_sharing_repo.share_emoji_file.call_args_list[0].kwargs[
                "preferences"
            ]
        )
        second_preferences = (
            mock_file_sharing_repo.share_emoji_file.call_args_list[1].kwargs[
                "preferences"
            ]
        )

        assert first_preferences.include_upload_instructions is True
        assert second_preferences.include_upload_instructions is False
