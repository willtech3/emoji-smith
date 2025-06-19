"""Tests for emoji sharing domain service."""

import pytest
from emojismith.domain.services.emoji_sharing_service import (
    EmojiSharingService,
    EmojiSharingContext,
    WorkspaceType,
    DirectEmojiUploadStrategy,
    FileSharingFallbackStrategy,
)
from emojismith.domain.entities.generated_emoji import GeneratedEmoji
from shared.domain.entities.slack_message import SlackMessage
from shared.domain.value_objects import (
    EmojiSharingPreferences,
    ShareLocation,
    InstructionVisibility,
    ImageSize,
)


class TestEmojiSharingService:
    """Test emoji sharing service determines correct strategy."""

    @pytest.fixture
    def sharing_service(self):
        """Create emoji sharing service."""
        return EmojiSharingService()

    @pytest.fixture
    def sample_emoji(self):
        """Create sample generated emoji."""
        return GeneratedEmoji(name="test_emoji", image_data=b"fake_png_data")

    @pytest.fixture
    def sample_message(self):
        """Create sample Slack message."""
        return SlackMessage(
            text="Generate a facepalm emoji",
            user_id="U123456",
            channel_id="C789012",
            timestamp="1234567890.123456",
            team_id="T999999",
        )

    @pytest.fixture
    def channel_sharing_prefs(self):
        """Create preferences for channel sharing."""
        return EmojiSharingPreferences(
            share_location=ShareLocation.ORIGINAL_CHANNEL,
            instruction_visibility=InstructionVisibility.EVERYONE,
            image_size=ImageSize.EMOJI_SIZE,
        )

    def test_uses_direct_upload_for_enterprise_grid(
        self, sharing_service, sample_emoji, sample_message, channel_sharing_prefs
    ):
        """Test Enterprise Grid workspaces use direct emoji upload."""
        # Arrange
        context = EmojiSharingContext(
            emoji=sample_emoji,
            original_message=sample_message,
            preferences=channel_sharing_prefs,
            workspace_type=WorkspaceType.ENTERPRISE_GRID,
        )

        # Act
        strategy = sharing_service.determine_sharing_strategy(context)

        # Assert
        assert isinstance(strategy, DirectEmojiUploadStrategy)

    def test_uses_file_sharing_for_standard_workspace(
        self, sharing_service, sample_emoji, sample_message, channel_sharing_prefs
    ):
        """Test standard workspaces use file sharing fallback."""
        # Arrange
        context = EmojiSharingContext(
            emoji=sample_emoji,
            original_message=sample_message,
            preferences=channel_sharing_prefs,
            workspace_type=WorkspaceType.STANDARD,
        )

        # Act
        strategy = sharing_service.determine_sharing_strategy(context)

        # Assert
        assert isinstance(strategy, FileSharingFallbackStrategy)
        assert strategy.preferences == channel_sharing_prefs

    def test_uses_file_sharing_for_free_workspace(
        self, sharing_service, sample_emoji, sample_message, channel_sharing_prefs
    ):
        """Test free workspaces use file sharing fallback."""
        # Arrange
        context = EmojiSharingContext(
            emoji=sample_emoji,
            original_message=sample_message,
            preferences=channel_sharing_prefs,
            workspace_type=WorkspaceType.FREE,
        )

        # Act
        strategy = sharing_service.determine_sharing_strategy(context)

        # Assert
        assert isinstance(strategy, FileSharingFallbackStrategy)

    def test_file_sharing_strategy_preserves_thread_preferences(
        self, sharing_service, sample_emoji, sample_message
    ):
        """Test file sharing strategy maintains thread sharing preference."""
        # Arrange
        thread_prefs = EmojiSharingPreferences(
            share_location=ShareLocation.THREAD,
            instruction_visibility=InstructionVisibility.SUBMITTER_ONLY,
            image_size=ImageSize.EMOJI_SIZE,
            thread_ts="1234567890.123456",
        )
        context = EmojiSharingContext(
            emoji=sample_emoji,
            original_message=sample_message,
            preferences=thread_prefs,
            workspace_type=WorkspaceType.STANDARD,
        )

        # Act
        strategy = sharing_service.determine_sharing_strategy(context)

        # Assert
        assert isinstance(strategy, FileSharingFallbackStrategy)
        assert strategy.preferences.share_location == ShareLocation.THREAD
        assert strategy.preferences.thread_ts == "1234567890.123456"

    def test_workspace_type_is_stored(self, sharing_service):
        """Test service stores the workspace type provided at initialization."""
        # Default workspace type should be STANDARD
        assert sharing_service.workspace_type == WorkspaceType.STANDARD

        # Test with explicit workspace type
        enterprise_service = EmojiSharingService(
            workspace_type=WorkspaceType.ENTERPRISE_GRID
        )
        assert enterprise_service.workspace_type == WorkspaceType.ENTERPRISE_GRID


class TestEmojiSharingContext:
    """Test emoji sharing context entity."""

    def test_creates_valid_context(self):
        """Test creating a valid sharing context."""
        # Arrange
        emoji = GeneratedEmoji(name="test", image_data=b"data")
        message = SlackMessage(
            text="test",
            user_id="U123",
            channel_id="C123",
            timestamp="123.456",
            team_id="T999",
        )
        prefs = EmojiSharingPreferences(
            share_location=ShareLocation.ORIGINAL_CHANNEL,
            instruction_visibility=InstructionVisibility.EVERYONE,
            image_size=ImageSize.EMOJI_SIZE,
        )

        # Act
        context = EmojiSharingContext(
            emoji=emoji,
            original_message=message,
            preferences=prefs,
            workspace_type=WorkspaceType.STANDARD,
        )

        # Assert
        assert context.emoji == emoji
        assert context.original_message == message
        assert context.preferences == prefs
        assert context.workspace_type == WorkspaceType.STANDARD

    def test_context_is_immutable(self):
        """Test context cannot be modified after creation."""
        # Arrange
        context = EmojiSharingContext(
            emoji=GeneratedEmoji(name="test", image_data=b"data"),
            original_message=SlackMessage(
                text="test",
                user_id="U123",
                channel_id="C123",
                timestamp="123.456",
                team_id="T999",
            ),
            preferences=EmojiSharingPreferences(
                share_location=ShareLocation.ORIGINAL_CHANNEL,
                instruction_visibility=InstructionVisibility.EVERYONE,
                image_size=ImageSize.EMOJI_SIZE,
            ),
            workspace_type=WorkspaceType.STANDARD,
        )

        # Act & Assert
        with pytest.raises(AttributeError):
            context.workspace_type = WorkspaceType.ENTERPRISE_GRID
