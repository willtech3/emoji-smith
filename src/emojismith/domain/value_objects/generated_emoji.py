"""GeneratedEmoji value object."""

from dataclasses import dataclass
from io import BytesIO
from PIL import Image, UnidentifiedImageError


@dataclass(frozen=True)
class GeneratedEmoji:
    """Slack emoji image with validation."""

    name: str
    image_data: bytes

    def __post_init__(self) -> None:
        if len(self.image_data) >= 64_000:
            raise ValueError("Emoji image exceeds 64KB size limit")
        try:
            image = Image.open(BytesIO(self.image_data))
        except UnidentifiedImageError as exc:
            raise ValueError("Invalid image data") from exc

        if image.format != "PNG":
            raise ValueError("Emoji image must be PNG")
        if image.size != (128, 128):
            raise ValueError("Emoji image must be 128x128 pixels")
