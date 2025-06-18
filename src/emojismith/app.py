"""FastAPI application factory."""

import logging
import os

from dotenv import load_dotenv
from openai import AsyncOpenAI
from slack_sdk.web.async_client import AsyncWebClient

from emojismith.application.services.emoji_service import EmojiCreationService
from emojismith.domain.services.emoji_validation_service import EmojiValidationService
from emojismith.domain.services.generation_service import EmojiGenerationService
from emojismith.infrastructure.image.pil_image_validator import PILImageValidator
from emojismith.infrastructure.image.processing import PillowImageProcessor
from emojismith.infrastructure.openai.openai_api import OpenAIAPIRepository
from emojismith.infrastructure.slack.slack_api import SlackAPIRepository

# Profile imports to identify bottlenecks
logger = logging.getLogger(__name__)
logger.info("📦 All imports completed - profiling will happen in functions")


def create_worker_emoji_service() -> EmojiCreationService:
    """Create emoji service instance for the background worker."""
    load_dotenv()

    slack_token = os.getenv("SLACK_BOT_TOKEN")
    openai_api_key = os.getenv("OPENAI_API_KEY")

    if not slack_token:
        raise ValueError("SLACK_BOT_TOKEN environment variable is required")
    if not openai_api_key:
        raise ValueError("OPENAI_API_KEY environment variable is required")

    slack_client = AsyncWebClient(token=slack_token)
    slack_repo = SlackAPIRepository(slack_client)

    openai_client = AsyncOpenAI(api_key=openai_api_key)
    chat_model = os.getenv("OPENAI_CHAT_MODEL", "o3")
    openai_repo = OpenAIAPIRepository(openai_client, model=chat_model)

    image_processor = PillowImageProcessor()
    image_validator = PILImageValidator()
    emoji_validation_service = EmojiValidationService(image_validator)

    generator = EmojiGenerationService(
        openai_repo=openai_repo,
        image_processor=image_processor,
        emoji_validator=emoji_validation_service,
    )

    from emojismith.infrastructure.slack.slack_file_sharing import (
        SlackFileSharingRepository,
    )

    file_sharing_repo = SlackFileSharingRepository(slack_client)

    return EmojiCreationService(
        slack_repo=slack_repo,
        emoji_generator=generator,
        job_queue=None,
        file_sharing_repo=file_sharing_repo,
    )


def create_app():  # type: ignore[no-untyped-def]
    """Placeholder function - worker Lambda shouldn't need FastAPI app."""
    # TODO: Remove this function when worker Lambda is converted to SQS event handler
    from fastapi import FastAPI

    return FastAPI(title="Worker Lambda - Should not receive HTTP requests")
