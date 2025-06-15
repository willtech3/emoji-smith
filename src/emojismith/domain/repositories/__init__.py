"""Domain repositories."""

from .slack_repository import SlackRepository
from .image_processor import ImageProcessor

__all__ = ["SlackRepository", "ImageProcessor"]
