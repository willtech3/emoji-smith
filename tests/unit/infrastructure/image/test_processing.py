"""Tests for PillowImageProcessor."""

from io import BytesIO
from PIL import Image
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


def test_processor_iterative_compression(monkeypatch) -> None:
    """Processor retries compression until size target is met."""
    processor = PillowImageProcessor(max_size=100)
    data = _create_image()

    calls = []

    def fake_encode(img, colors):
        calls.append(colors)
        if len(calls) == 1:
            return b"x" * 200  # too large
        return b"x" * 50  # acceptable

    monkeypatch.setattr(processor, "_encode", fake_encode)
    out = processor.process(data)
    assert len(out) == 50
    assert calls == [256, 128]
