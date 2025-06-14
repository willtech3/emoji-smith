"""Generated emoji entity and validation."""

from dataclasses import dataclass
from io import BytesIO
from typing import ClassVar
from PIL import Image


@dataclass(frozen=True)
class GeneratedEmoji:
    """Entity representing a generated emoji image."""

    image_data: bytes
    name: str
    MAX_SIZE: ClassVar[int] = 64 * 1024

    def __post_init__(self) -> None:
        if not self.image_data:
            raise ValueError("image_data is required")
        if not self.name:
            raise ValueError("name is required")

        with Image.open(BytesIO(self.image_data)) as img:
            if img.format != "PNG":
                raise ValueError("emoji must be PNG format")
            if img.width != 128 or img.height != 128:
                raise ValueError("emoji must be 128x128 pixels")

        if len(self.image_data) >= self.MAX_SIZE:
            raise ValueError("emoji must be smaller than 64KB")
