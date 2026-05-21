"""Tests for PillowImageProcessor."""

import logging
from io import BytesIO

import pytest
from PIL import Image

from emojismith.infrastructure.image.processing import PillowImageProcessor


def _create_image(size=(1024, 1024)) -> bytes:
    img = Image.new("RGBA", size, "green")
    bio = BytesIO()
    img.save(bio, format="PNG")
    return bio.getvalue()


@pytest.mark.unit()
def test_processor_resizes_and_compresses() -> None:
    processor = PillowImageProcessor()
    data = _create_image()
    out = processor.process(data)
    with Image.open(BytesIO(out)) as img:
        assert img.width == 128
        assert img.height == 128
        assert img.format == "PNG"
    assert len(out) < 64 * 1024


@pytest.mark.unit()
def test_image_processor_reduces_colors_iteratively(monkeypatch) -> None:
    processor = PillowImageProcessor()

    calls: list[int] = []

    class DummyQuantized:
        def __init__(self, colors: int) -> None:
            self._colors = colors

        def save(self, output: BytesIO, format: str, **kwargs) -> None:
            size = 70 * 1024 if self._colors == 256 else 1024
            output.write(b"x" * size)

    def fake_quantize(self, colors: int) -> DummyQuantized:
        calls.append(colors)
        return DummyQuantized(colors)

    monkeypatch.setattr(Image.Image, "quantize", fake_quantize)

    image_bytes = _create_image()

    # Force fallback to quantization by making standard RGBA save exceed 64KB
    def fake_save(self, output: BytesIO, format: str, *args, **kwargs) -> None:
        output.write(b"y" * (70 * 1024))

    monkeypatch.setattr(Image.Image, "save", fake_save)

    out = processor.process(image_bytes)

    assert len(out) == 1024
    assert calls == [256, 128]


@pytest.mark.unit()
def test_image_processor_uses_lossless_when_under_limit(monkeypatch, caplog) -> None:
    processor = PillowImageProcessor()

    quantize_called = False

    def fake_quantize(self, colors: int):
        nonlocal quantize_called
        quantize_called = True
        return self

    monkeypatch.setattr(Image.Image, "quantize", fake_quantize)

    with caplog.at_level(logging.INFO):
        out = processor.process(_create_image())

    # Verify that quantize was NEVER called since solid green 128x128 fits losslessly
    assert not quantize_called
    assert len(out) < 64 * 1024

    # Find the log record to verify colors_used is "lossless"
    processed_record = None
    for record in caplog.records:
        if "image processed" in record.message:
            processed_record = record
            break

    assert processed_record is not None
    assert processed_record.colors_used == "lossless"


@pytest.mark.unit()
def test_image_processor_logs_processing_metrics(caplog) -> None:
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
    assert hasattr(processed_record, "original")
    assert hasattr(processed_record, "final")
    assert hasattr(processed_record, "compression_ratio")
    assert hasattr(processed_record, "colors_used")


@pytest.mark.unit()
def test_raises_when_image_too_large(monkeypatch) -> None:
    processor = PillowImageProcessor()

    class AlwaysBig:
        def save(self, output: BytesIO, format: str, **kwargs) -> None:
            output.write(b"y" * (70 * 1024))

    def big_quantize(self, colors: int) -> AlwaysBig:
        return AlwaysBig()

    monkeypatch.setattr(Image.Image, "quantize", big_quantize)

    image_bytes = _create_image()

    # Force fallback to quantization by making standard RGBA save exceed 64KB
    def fake_save(self, output: BytesIO, format: str, *args, **kwargs) -> None:
        output.write(b"y" * (70 * 1024))

    monkeypatch.setattr(Image.Image, "save", fake_save)

    with pytest.raises(ValueError):
        processor.process(image_bytes)
