"""Image processing utilities for emoji generation."""

from io import BytesIO
import logging
from typing import Protocol
from PIL import Image

# Use LANCZOS if available, fall back to BICUBIC for older stubs
RESAMPLE = getattr(Image, "LANCZOS", Image.BICUBIC)  # type: ignore[attr-defined]


class ImageProcessor(Protocol):
    """Protocol for image processing implementations."""

    def process(self, image_data: bytes) -> bytes:
        """Process raw image data and return optimized PNG."""
        ...


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

            for colors in (256, 128, 64, 32):
                data = self._quantize_and_save(img, colors)
                self._logger.debug(
                    "quantized with %d colors: %d bytes", colors, len(data)
                )
                if len(data) < 64 * 1024:
                    break
            else:
                raise ValueError("processed image too large")

        self._logger.info(
            "image processed", extra={"original": original_size, "final": len(data)}
        )
        return data

    def _quantize_and_save(self, img: Image.Image, colors: int) -> bytes:
        output = BytesIO()
        img.quantize(colors=colors).save(output, format="PNG", optimize=True)
        return output.getvalue()
