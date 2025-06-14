"""Image processing utilities for emoji generation."""

from io import BytesIO
import logging
from typing import Protocol

from PIL import Image


class ImageProcessor(Protocol):
    """Protocol for image processing implementations."""

    def process(self, image_data: bytes) -> bytes:
        """Process raw image data and return optimized PNG."""
        ...


class PillowImageProcessor:
    """Process images using Pillow with iterative compression."""

    def __init__(self, target_size: int = 128, max_size_kb: int = 64) -> None:
        self._target_size = target_size
        self._max_size = max_size_kb * 1024
        self._logger = logging.getLogger(__name__)

    def process(self, image_data: bytes) -> bytes:
        with Image.open(BytesIO(image_data)) as img:
            img = img.convert("RGBA")
            img = img.resize((self._target_size, self._target_size))

            for compress_level in range(9, 0, -1):
                for colors in (256, 128, 64, 32, 16, 8):
                    attempt = img.quantize(colors=colors)
                    output = BytesIO()
                    attempt.save(
                        output,
                        format="PNG",
                        optimize=True,
                        compress_level=compress_level,
                    )
                    data = output.getvalue()
                    self._logger.debug(
                        "compression=%d colors=%d size=%d",
                        compress_level,
                        colors,
                        len(data),
                    )
                    if len(data) < self._max_size:
                        self._logger.info(
                            "Processed image %d bytes with %d colors level %d",
                            len(data),
                            colors,
                            compress_level,
                        )
                        return data

            self._logger.warning(
                "Unable to compress image below %d bytes, final size %d",
                self._max_size,
                len(data),
            )
            raise ValueError("processed image too large")
