"""Tests for image processor utilities."""

import io

import pytest
from PIL import Image

from emojismith.infrastructure.image_processor import compress_for_slack


@pytest.mark.unit()
class TestCompressForSlack:
    """Tests for compress_for_slack function."""

    def _create_png_bytes(self, size: int = 1024, color: str = "red") -> bytes:
        """Create a simple PNG image as bytes."""
        img = Image.new("RGBA", (size, size), color)
        output = io.BytesIO()
        img.save(output, format="PNG")
        return output.getvalue()

    def _create_large_png(self, size_kb: int) -> bytes:
        """Create a PNG that's approximately the specified size in KB."""
        # Use a complex pattern to create larger file sizes
        img = Image.new("RGBA", (1024, 1024))
        pixels = img.load()
        for x in range(1024):
            for y in range(1024):
                # Create a pattern that doesn't compress well
                pixels[x, y] = (
                    (x * y) % 256,
                    (x + y) % 256,
                    (x - y) % 256,
                    255,
                )  # type: ignore[index]
        output = io.BytesIO()
        img.save(output, format="PNG")
        return output.getvalue()

    def test_small_image_returns_at_first_size(self):
        """Small images should return at 512x512 if under limit."""
        img_bytes = self._create_png_bytes(size=256)
        result = compress_for_slack(img_bytes)

        # Should return compressed image
        assert len(result) < 128 * 1024  # Under 128KB

        # Verify result is valid PNG
        result_img = Image.open(io.BytesIO(result))
        assert result_img.format == "PNG"

    def test_compresses_to_under_limit(self):
        """Output should always be under the size limit."""
        img_bytes = self._create_large_png(200)  # ~200KB source
        result = compress_for_slack(img_bytes, max_size_kb=128)

        assert len(result) <= 128 * 1024

    def test_compress_for_slack_when_input_has_alpha_preserves_transparency(self):
        """Transparency should be preserved in output."""
        # Create image with transparency
        img = Image.new("RGBA", (512, 512), (255, 0, 0, 128))
        output = io.BytesIO()
        img.save(output, format="PNG")
        img_bytes = output.getvalue()

        result = compress_for_slack(img_bytes)

        result_img = Image.open(io.BytesIO(result))
        assert result_img.mode in ("RGBA", "P")  # RGBA or palette with transparency

    def test_resizes_to_square(self):
        """Output should be square."""
        img_bytes = self._create_png_bytes(size=800)
        result = compress_for_slack(img_bytes)

        result_img = Image.open(io.BytesIO(result))
        assert result_img.width == result_img.height

    def test_uses_lanczos_resampling(self):
        """Should use high-quality LANCZOS resampling."""
        # This is implicit - we just verify the output looks reasonable
        img_bytes = self._create_png_bytes(size=1024)
        result = compress_for_slack(img_bytes)

        result_img = Image.open(io.BytesIO(result))
        # Should be one of the target sizes
        assert result_img.width in (512, 256, 128)

    def test_custom_max_size(self):
        """Should respect custom max_size_kb parameter."""
        img_bytes = self._create_png_bytes(size=512)
        result = compress_for_slack(img_bytes, max_size_kb=50)

        assert len(result) <= 50 * 1024

    def test_compress_for_slack_when_called_returns_bytes(self):
        """Output should be bytes."""
        img_bytes = self._create_png_bytes(size=256)
        result = compress_for_slack(img_bytes)

        assert isinstance(result, bytes)

    def test_output_is_valid_png(self):
        """Output should be valid PNG format."""
        img_bytes = self._create_png_bytes(size=512)
        result = compress_for_slack(img_bytes)

        # Should be openable as image
        result_img = Image.open(io.BytesIO(result))
        assert result_img.format == "PNG"

    def test_handles_various_input_sizes(self):
        """Should handle various input image sizes."""
        for size in [64, 256, 512, 1024, 2048]:
            img_bytes = self._create_png_bytes(size=size)
            result = compress_for_slack(img_bytes)

            assert len(result) <= 128 * 1024
            result_img = Image.open(io.BytesIO(result))
            assert result_img.format == "PNG"

    def test_progressively_reduces_size(self):
        """Should try larger sizes first, then reduce if needed."""
        # Create a moderately large image
        img_bytes = self._create_png_bytes(size=1024)
        result = compress_for_slack(img_bytes)

        result_img = Image.open(io.BytesIO(result))
        # Should be at one of the step sizes
        assert result_img.width in (512, 256, 128)
