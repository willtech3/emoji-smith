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


class _IterativeProcessor(PillowImageProcessor):
    """Processor that simulates iterative compression behaviour."""

    def _quantize_and_save(self, img: Image.Image, colors: int) -> bytes:  # type: ignore[override]
        if colors == 256:
            return b"x" * (70 * 1024)
        return b"x" * 1024


def test_iterative_compression() -> None:
    processor = _IterativeProcessor()
    out = processor.process(_create_image())
    assert len(out) == 1024


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


class _AlwaysLargeProcessor(PillowImageProcessor):
    """Processor that never compresses below the threshold."""

    def _quantize_and_save(self, img: Image.Image, colors: int) -> bytes:  # type: ignore[override]
        return b"y" * (70 * 1024)


def test_raises_when_image_too_large() -> None:
    processor = _AlwaysLargeProcessor()
    with pytest.raises(ValueError):
        processor.process(_create_image())
