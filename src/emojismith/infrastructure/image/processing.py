"""Image processing utilities for emoji generation."""

from io import BytesIO
from typing import Protocol
from PIL import Image


class ImageProcessor(Protocol):
    """Protocol for image processing implementations."""

    def process(self, image_data: bytes) -> bytes:
        """Process raw image data and return optimized PNG."""
        ...


class PillowImageProcessor:
    """Process images using Pillow."""

    def process(self, image_data: bytes) -> bytes:
        with Image.open(BytesIO(image_data)) as img:
            img = img.convert("RGBA")
            img = img.resize((128, 128))
            img = img.quantize(colors=256)
            output = BytesIO()
            img.save(output, format="PNG", optimize=True)
            data = output.getvalue()
            if len(data) >= 64 * 1024:
                raise ValueError("processed image too large")
            return data
