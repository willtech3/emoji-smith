"""Tests for EmojiValidationService."""

import os

import pytest

from emojismith.domain.entities.generated_emoji import GeneratedEmoji
from emojismith.domain.services.emoji_validation_service import EmojiValidationService
from emojismith.infrastructure.image.pil_image_validator import PILImageValidator


@pytest.mark.unit()
class TestEmojiValidationService:
    @pytest.fixture()
    def fixtures_dir(self):
        """Path to test fixtures directory."""
        return os.path.join(os.path.dirname(__file__), "../../../fixtures/images")

    @pytest.fixture()
    def image_validator(self):
        """Real PILImageValidator for testing."""
        return PILImageValidator()

    @pytest.fixture()
    def validation_service(self, image_validator):
        """EmojiValidationService with real validator."""
        return EmojiValidationService(image_validator)

    @pytest.fixture()
    def valid_image_data(self, fixtures_dir):
        """Load valid PNG image data."""
        with open(os.path.join(fixtures_dir, "valid_emoji.png"), "rb") as f:
            return f.read()

    @pytest.fixture()
    def wrong_size_image_data(self, fixtures_dir):
        """Load wrong size PNG image data."""
        with open(os.path.join(fixtures_dir, "wrong_size.png"), "rb") as f:
            return f.read()

    @pytest.fixture()
    def wrong_format_image_data(self, fixtures_dir):
        """Load JPEG image data."""
        with open(os.path.join(fixtures_dir, "wrong_format.jpg"), "rb") as f:
            return f.read()

    @pytest.fixture()
    def corrupted_image_data(self, fixtures_dir):
        """Load corrupted PNG image data."""
        with open(os.path.join(fixtures_dir, "corrupted.png"), "rb") as f:
            return f.read()

    def test_validate_and_create_emoji_success(
        self, validation_service, valid_image_data
    ):
        """Test successful emoji creation with valid 128x128 PNG image."""
        name = "test_emoji"

        # Act - should succeed with valid image
        result = validation_service.validate_and_create_emoji(valid_image_data, name)

        # Assert
        assert isinstance(result, GeneratedEmoji)
        assert result.image_data == valid_image_data
        assert result.name == name
        # No exception should be raised for valid image

    def test_validate_and_create_emoji_wrong_size_fails(
        self, validation_service, wrong_size_image_data
    ):
        """Test emoji creation fails with wrong size image (64x64 not 128x128)."""
        name = "test_emoji"

        # Act & Assert
        with pytest.raises(ValueError, match="emoji must be 128x128 pixels"):
            validation_service.validate_and_create_emoji(wrong_size_image_data, name)

    def test_validate_and_create_emoji_wrong_format_fails(
        self, validation_service, wrong_format_image_data
    ):
        """Test emoji creation fails with wrong format (JPEG instead of PNG)."""
        name = "test_emoji"

        # Act & Assert
        with pytest.raises(ValueError, match="emoji must be PNG format"):
            validation_service.validate_and_create_emoji(wrong_format_image_data, name)

    def test_validate_and_create_emoji_corrupted_fails(
        self, validation_service, corrupted_image_data
    ):
        """Test emoji creation fails with corrupted image data."""
        name = "test_emoji"

        # Act & Assert
        with pytest.raises(ValueError, match="Invalid image data"):
            validation_service.validate_and_create_emoji(corrupted_image_data, name)

    def test_entity_validation_still_applies(
        self, validation_service, valid_image_data
    ):
        """Test entity-level validation applies even if image validation would pass."""
        # Test empty name still fails (entity-level validation)
        with pytest.raises(ValueError, match="name is required"):
            validation_service.validate_and_create_emoji(valid_image_data, "")

        # Test empty image data still fails (but caught by image validator first)
        with pytest.raises(ValueError, match="Invalid image data"):
            validation_service.validate_and_create_emoji(b"", "test")

    def test_get_image_dimensions(
        self, image_validator, valid_image_data, wrong_size_image_data
    ):
        """Test getting image dimensions from real image data."""
        # Test valid 128x128 image
        width, height = image_validator.get_image_dimensions(valid_image_data)
        assert width == 128
        assert height == 128

        # Test wrong size 64x64 image
        width, height = image_validator.get_image_dimensions(wrong_size_image_data)
        assert width == 64
        assert height == 64
