"""Tests for PillowImageProcessor."""

from io import BytesIO
import pytest
from PIL import Image
from emojismith.infrastructure.image.processing import PillowImageProcessor


def _create_image(size: tuple[int, int] = (1024, 1024)) -> bytes:
    img = Image.effect_noise(size, 100).convert("RGBA")
    bio = BytesIO()
    img.save(bio, format="PNG")
    return bio.getvalue()


def test_processor_resizes_and_compresses() -> None:
    processor = PillowImageProcessor()
    data = _create_image()
    out = processor.process(data)
    with Image.open(BytesIO(out)) as img:
        assert img.width == 128
        assert img.height == 128
        assert img.format == "PNG"
    assert len(out) < 64 * 1024


def test_processor_raises_on_size_limit() -> None:
    processor = PillowImageProcessor(max_size_kb=1)
    data = _create_image()
    with pytest.raises(ValueError):
        processor.process(data)
