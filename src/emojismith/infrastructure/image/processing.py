"""Image processing utilities for emoji generation."""

from io import BytesIO
from dataclasses import dataclass, field
from typing import Protocol
import logging
from PIL import Image


class ImageProcessor(Protocol):
    """Protocol for image processing implementations."""

    def process(self, image_data: bytes) -> bytes:
        """Process raw image data and return optimized PNG."""
        ...


@dataclass
class PillowImageProcessor:
    """Process images using Pillow with iterative compression."""

    max_size: int = 64 * 1024
    _logger: logging.Logger = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._logger = logging.getLogger(__name__)

    def process(self, image_data: bytes) -> bytes:
        with Image.open(BytesIO(image_data)) as img:
            img = img.convert("RGBA")
            img = img.resize((128, 128))

            for colors in (256, 128, 64, 32, 16):
                data = self._encode(img, colors)
                self._logger.info(
                    "compressed image to %d bytes using %d colors", len(data), colors
                )
                if len(data) < self.max_size:
                    return data

        raise ValueError("processed image too large")

    def _encode(self, img: Image.Image, colors: int) -> bytes:
        quantized = img.quantize(colors=colors)
        output = BytesIO()
        quantized.save(output, format="PNG", optimize=True)
        return output.getvalue()
