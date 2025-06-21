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


def test_pillow_processor_resizes_and_compresses() -> None:
    processor = PillowImageProcessor()
    data = _create_image()
    out = processor.process(data)
    with Image.open(BytesIO(out)) as img:
        assert img.width == 128
        assert img.height == 128
        assert img.format == "PNG"
    assert len(out) < 64 * 1024


def test_pillow_processor_iteratively_compresses(monkeypatch) -> None:
    processor = PillowImageProcessor()

    calls: list[int] = []

    class DummyQuantized:
        def __init__(self, colors: int) -> None:
            self._colors = colors

        def save(self, output: BytesIO, format: str, optimize: bool = True) -> None:
            size = 70 * 1024 if self._colors == 256 else 1024
            output.write(b"x" * size)

    def fake_quantize(self, colors: int) -> DummyQuantized:
        calls.append(colors)
        return DummyQuantized(colors)

    monkeypatch.setattr(Image.Image, "quantize", fake_quantize)

    out = processor.process(_create_image())

    assert len(out) == 1024
    assert calls == [256, 128]


def test_pillow_processor_logs_metrics(caplog) -> None:
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


def test_pillow_processor_raises_when_image_too_large(monkeypatch) -> None:
    processor = PillowImageProcessor()

    class AlwaysBig:
        def save(self, output: BytesIO, format: str, optimize: bool = True) -> None:
            output.write(b"y" * (70 * 1024))

    def big_quantize(self, colors: int) -> AlwaysBig:
        return AlwaysBig()

    monkeypatch.setattr(Image.Image, "quantize", big_quantize)

    with pytest.raises(ValueError):
        processor.process(_create_image())
