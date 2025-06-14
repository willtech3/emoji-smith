"""Tests for GeneratedEmoji entity."""

from io import BytesIO
from PIL import Image
import pytest
from emojismith.domain.entities.generated_emoji import GeneratedEmoji


def _create_png_bytes(color: str = "red", size: int = 128) -> bytes:
    img = Image.new("RGBA", (size, size), color)
    bio = BytesIO()
    img.save(bio, format="PNG")
    return bio.getvalue()


class TestGeneratedEmoji:
    def test_valid_emoji(self) -> None:
        data = _create_png_bytes()
        emoji = GeneratedEmoji(image_data=data, name="test")
        assert emoji.name == "test"

    def test_invalid_format(self) -> None:
        # Save as JPEG to break format
        img = Image.new("RGB", (128, 128), "blue")
        bio = BytesIO()
        img.save(bio, format="JPEG")
        jpeg_data = bio.getvalue()
        with pytest.raises(ValueError, match="PNG"):
            GeneratedEmoji(image_data=jpeg_data, name="bad")

    def test_invalid_size(self) -> None:
        data = _create_png_bytes(size=64)
        with pytest.raises(ValueError, match="128x128"):
            GeneratedEmoji(image_data=data, name="small")

    def test_file_too_large(self) -> None:
        data = _create_png_bytes()
        big_data = data + b"0" * (64 * 1024)
        with pytest.raises(ValueError, match="64KB"):
            GeneratedEmoji(image_data=big_data, name="big")
