"""Tests for PillowImageProcessor."""

from io import BytesIO
import logging
from PIL import Image
import pytest
from emojismith.infrastructure.image.processing import PillowImageProcessor


def _create_image(size=(1024, 1024)) -> bytes:
    img = Image.new("RGBA", size, "green")
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


def test_logs_metrics(caplog) -> None:
    processor = PillowImageProcessor()
    with caplog.at_level(logging.INFO):
        processor.process(_create_image())

    # Find the "image processed" log record
    processed_record = None
    for record in caplog.records:
        if "image processed" in record.message:
            processed_record = record
            break

    assert processed_record is not None
    assert "original" in processed_record.__dict__
    assert "final" in processed_record.__dict__
    assert "compression_ratio" in processed_record.__dict__
    assert "colors_used" in processed_record.__dict__


def test_raises_when_image_too_large(monkeypatch) -> None:
    """Processor raises when quantized image never shrinks below limit."""
    processor = PillowImageProcessor()

    # Force Pillow to produce oversized output without touching private methods
    original_save = Image.Image.save

    def big_save(self, fp, format=None, optimize=True):
        original_save(self, fp, format=format, optimize=optimize)
        fp.write(b"x" * (70 * 1024))

    monkeypatch.setattr(Image.Image, "save", big_save)

    with pytest.raises(ValueError):
        processor.process(_create_image())
