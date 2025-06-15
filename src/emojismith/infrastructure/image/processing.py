"""Image processing utilities for emoji generation."""

from io import BytesIO
import logging
from PIL import Image
from emojismith.domain.repositories.image_processor import ImageProcessor  # noqa: F401

# Use LANCZOS if available, fall back to BICUBIC for older stubs
RESAMPLE = getattr(Image, "LANCZOS", Image.BICUBIC)  # type: ignore[attr-defined]


class PillowImageProcessor:
    """Process images using Pillow."""

    def __init__(self) -> None:
        self._logger = logging.getLogger(__name__)

    def process(self, image_data: bytes) -> bytes:
        """Resize and compress image to Slack's emoji requirements."""
        original_size = len(image_data)
        with Image.open(BytesIO(image_data)) as img:
            img = img.convert("RGBA")
            img = img.resize((128, 128), RESAMPLE)

            final_colors = 256  # Track the final color count used
            for colors in (256, 128, 64, 32):
                data = self._quantize_and_save(img, colors)
                self._logger.debug(
                    "quantized with %d colors: %d bytes (%.1f%% of original)",
                    colors,
                    len(data),
                    (len(data) / original_size) * 100,
                )
                if len(data) < 64 * 1024:
                    final_colors = colors
                    break
            else:
                raise ValueError("processed image too large")

        self._logger.info(
            "image processed",
            extra={
                "original": original_size,
                "final": len(data),
                "compression_ratio": round(original_size / len(data), 2),
                "colors_used": final_colors,
            },
        )
        return data

    def _quantize_and_save(self, img: Image.Image, colors: int) -> bytes:
        """Quantize image to reduce colors and file size.

        Args:
            img: PIL Image to quantize
            colors: Number of colors in the palette (fewer = smaller file)

        Returns:
            PNG bytes of the quantized image
        """
        output = BytesIO()
        img.quantize(colors=colors).save(output, format="PNG", optimize=True)
        return output.getvalue()
