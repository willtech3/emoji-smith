"""Tests for PILImageValidator."""

from io import BytesIO
from PIL import Image
import pytest
from emojismith.infrastructure.image.pil_image_validator import PILImageValidator


def _create_png_bytes(color: str = "red", size: tuple[int, int] = (128, 128)) -> bytes:
    """Helper to create PNG image bytes."""
    img = Image.new("RGBA", size, color)
    bio = BytesIO()
    img.save(bio, format="PNG")
    return bio.getvalue()


def _create_jpeg_bytes(
    color: str = "blue", size: tuple[int, int] = (128, 128)
) -> bytes:
    """Helper to create JPEG image bytes."""
    img = Image.new("RGB", size, color)
    bio = BytesIO()
    img.save(bio, format="JPEG")
    return bio.getvalue()


class TestPILImageValidator:
    @pytest.fixture
    def validator(self):
        """PILImageValidator instance for testing."""
        return PILImageValidator()

    def test_validate_emoji_format_success(self, validator):
        """Test validation passes for valid 128x128 PNG."""
        valid_png = _create_png_bytes()

        # Should not raise exception
        validator.validate_emoji_format(valid_png)

    def test_validate_emoji_format_invalid_format(self, validator):
        """Test validation fails for non-PNG format."""
        jpeg_data = _create_jpeg_bytes()

        with pytest.raises(ValueError, match="emoji must be PNG format"):
            validator.validate_emoji_format(jpeg_data)

    def test_validate_emoji_format_invalid_dimensions(self, validator):
        """Test validation fails for wrong dimensions."""
        # Test wrong width
        wrong_size_png = _create_png_bytes(size=(64, 128))
        with pytest.raises(ValueError, match="emoji must be 128x128 pixels"):
            validator.validate_emoji_format(wrong_size_png)

        # Test wrong height
        wrong_size_png = _create_png_bytes(size=(128, 64))
        with pytest.raises(ValueError, match="emoji must be 128x128 pixels"):
            validator.validate_emoji_format(wrong_size_png)

        # Test both wrong
        wrong_size_png = _create_png_bytes(size=(64, 64))
        with pytest.raises(ValueError, match="emoji must be 128x128 pixels"):
            validator.validate_emoji_format(wrong_size_png)

    def test_validate_emoji_format_corrupted_data(self, validator):
        """Test validation fails for corrupted image data."""
        corrupted_data = b"not_an_image"

        with pytest.raises(ValueError, match="Invalid image data"):
            validator.validate_emoji_format(corrupted_data)

    def test_get_image_dimensions_success(self, validator):
        """Test getting dimensions from valid image."""
        png_data = _create_png_bytes(size=(256, 256))

        width, height = validator.get_image_dimensions(png_data)

        assert width == 256
        assert height == 256

    def test_get_image_dimensions_different_formats(self, validator):
        """Test getting dimensions works for different formats."""
        # PNG
        png_data = _create_png_bytes(size=(100, 200))
        assert validator.get_image_dimensions(png_data) == (100, 200)

        # JPEG
        jpeg_data = _create_jpeg_bytes(size=(300, 400))
        assert validator.get_image_dimensions(jpeg_data) == (300, 400)

    def test_get_image_dimensions_corrupted_data(self, validator):
        """Test getting dimensions fails for corrupted data."""
        corrupted_data = b"not_an_image"

        with pytest.raises(ValueError, match="Cannot read image dimensions"):
            validator.get_image_dimensions(corrupted_data)
