"""Tests for GeneratedEmoji value object."""

from io import BytesIO

import pytest
from PIL import Image

from emojismith.domain.value_objects import GeneratedEmoji


class TestGeneratedEmoji:
    """Validate GeneratedEmoji rules."""

    @staticmethod
    def _make_png(size: tuple[int, int] = (128, 128)) -> bytes:
        img = Image.new("RGBA", size, (255, 0, 0, 0))
        buf = BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    def test_valid_generated_emoji(self) -> None:
        data = self._make_png()
        emoji = GeneratedEmoji(name="test", image_data=data)
        assert emoji.name == "test"

    def test_rejects_non_png(self) -> None:
        img = Image.new("RGB", (128, 128), (0, 0, 0))
        buf = BytesIO()
        img.save(buf, format="JPEG")
        with pytest.raises(ValueError):
            GeneratedEmoji(name="test", image_data=buf.getvalue())

    def test_rejects_wrong_size(self) -> None:
        data = self._make_png(size=(64, 64))
        with pytest.raises(ValueError):
            GeneratedEmoji(name="test", image_data=data)

    def test_rejects_too_large(self) -> None:
        # create data >64KB by repeating
        data = self._make_png()
        large = data + b"0" * (64_000 - len(data) + 1)
        with pytest.raises(ValueError):
            GeneratedEmoji(name="test", image_data=large)
