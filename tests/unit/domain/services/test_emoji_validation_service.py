"""Tests for EmojiValidationService."""

import pytest
from unittest.mock import Mock
from emojismith.domain.services.emoji_validation_service import EmojiValidationService
from emojismith.domain.entities.generated_emoji import GeneratedEmoji


class TestEmojiValidationService:
    @pytest.fixture
    def mock_image_validator(self):
        """Mock ImageValidator for testing."""
        return Mock()

    @pytest.fixture
    def validation_service(self, mock_image_validator):
        """EmojiValidationService with mocked validator."""
        return EmojiValidationService(mock_image_validator)

    def test_validate_and_create_emoji_success(
        self, validation_service, mock_image_validator
    ):
        """Test successful emoji creation after validation."""
        image_data = b"fake_png_data"
        name = "test_emoji"

        # Mock validator passes validation
        mock_image_validator.validate_emoji_format.return_value = None

        # Act
        result = validation_service.validate_and_create_emoji(image_data, name)

        # Assert
        assert isinstance(result, GeneratedEmoji)
        assert result.image_data == image_data
        assert result.name == name
        mock_image_validator.validate_emoji_format.assert_called_once_with(image_data)

    def test_validate_and_create_emoji_validation_fails(
        self, validation_service, mock_image_validator
    ):
        """Test emoji creation fails when validation fails."""
        image_data = b"invalid_data"
        name = "test_emoji"

        # Mock validator raises validation error
        mock_image_validator.validate_emoji_format.side_effect = ValueError(
            "Invalid format"
        )

        # Act & Assert
        with pytest.raises(ValueError, match="Invalid format"):
            validation_service.validate_and_create_emoji(image_data, name)

        mock_image_validator.validate_emoji_format.assert_called_once_with(image_data)

    def test_entity_validation_still_applies(
        self, validation_service, mock_image_validator
    ):
        """Test entity-level validation applies even if image validation passes."""
        # Mock validator passes
        mock_image_validator.validate_emoji_format.return_value = None

        # Test empty name still fails (entity-level validation)
        with pytest.raises(ValueError, match="name is required"):
            validation_service.validate_and_create_emoji(b"data", "")

        # Test empty image data still fails (entity-level validation)
        with pytest.raises(ValueError, match="image_data is required"):
            validation_service.validate_and_create_emoji(b"", "test")
