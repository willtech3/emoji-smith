"""FastAPI application factory."""

import logging
import os

from dotenv import load_dotenv
from openai import AsyncOpenAI
from slack_sdk.web.async_client import AsyncWebClient

from emojismith.application.services.emoji_service import EmojiCreationService
from emojismith.application.use_cases.build_prompt_use_case import BuildPromptUseCase
from emojismith.domain.services.emoji_sharing_service import (
    EmojiSharingService,
    WorkspaceType,
)
from emojismith.domain.services.emoji_validation_service import EmojiValidationService
from emojismith.domain.services.style_template_manager import StyleTemplateManager
from emojismith.infrastructure.factories import ImageGeneratorFactory
from emojismith.infrastructure.image.pil_image_validator import PILImageValidator
from emojismith.infrastructure.image.processing import PillowImageProcessor
from emojismith.infrastructure.openai.openai_api import OpenAIAPIRepository
from emojismith.infrastructure.repositories.style_template_config_repository import (
    StyleTemplateConfigRepository,
)
from emojismith.infrastructure.slack.slack_api import SlackAPIRepository
from emojismith.infrastructure.slack.slack_file_sharing import (
    SlackFileSharingRepository,
)

# Profile imports to identify bottlenecks
logger = logging.getLogger(__name__)
logger.info("📦 All imports completed - profiling will happen in functions")


def create_worker_emoji_service() -> EmojiCreationService:
    """Create emoji service instance for the background worker."""
    load_dotenv()

    slack_token = os.getenv("SLACK_BOT_TOKEN")
    openai_api_key = os.getenv("OPENAI_API_KEY")
    google_api_key = os.getenv("GOOGLE_API_KEY")

    if not slack_token:
        raise ValueError("SLACK_BOT_TOKEN environment variable is required")
    if not openai_api_key:
        raise ValueError("OPENAI_API_KEY environment variable is required")
    # GOOGLE_API_KEY is optional - Gemini provider won't work without it

    slack_client = AsyncWebClient(token=slack_token)
    slack_repo = SlackAPIRepository(slack_client)

    # OpenAI client for prompt enhancement (chat completion)
    openai_client = AsyncOpenAI(api_key=openai_api_key)
    chat_model = os.getenv("OPENAI_CHAT_MODEL", "gpt-5")
    openai_repo = OpenAIAPIRepository(openai_client, model=chat_model)

    # Create image generator factory with both API keys
    image_generator_factory = ImageGeneratorFactory(
        openai_api_key=openai_api_key,
        google_api_key=google_api_key,
    )

    image_processor = PillowImageProcessor()
    image_validator = PILImageValidator()
    emoji_validation_service = EmojiValidationService(image_validator)

    # Create style template dependencies
    style_template_repository = StyleTemplateConfigRepository()
    style_template_manager = StyleTemplateManager(style_template_repository)

    # Create the build prompt use case (uses OpenAI for prompt enhancement)
    build_prompt_use_case = BuildPromptUseCase(
        prompt_enhancer=openai_repo,
        prompt_builder_service=None,  # Will use default PromptBuilderService
    )

    file_sharing_repo = SlackFileSharingRepository(slack_client)

    # Determine workspace type from environment
    workspace_type = WorkspaceType.STANDARD
    force_enterprise = os.getenv("EMOJISMITH_FORCE_ENTERPRISE", "false")

    # Validate environment variable value
    if force_enterprise.lower() not in ("true", "false"):
        logger.warning(
            f"Invalid value for EMOJISMITH_FORCE_ENTERPRISE: '{force_enterprise}'. "
            "Expected 'true' or 'false'. Defaulting to 'false'."
        )
        force_enterprise = "false"

    if force_enterprise.lower() == "true":
        workspace_type = WorkspaceType.ENTERPRISE_GRID

    # Create sharing service with injected workspace type
    sharing_service = EmojiSharingService(workspace_type=workspace_type)

    return EmojiCreationService(
        slack_repo=slack_repo,
        build_prompt_use_case=build_prompt_use_case,
        image_generator_factory=image_generator_factory,
        image_processor=image_processor,
        emoji_validator=emoji_validation_service,
        style_template_manager=style_template_manager,
        job_queue=None,
        file_sharing_repo=file_sharing_repo,
        sharing_service=sharing_service,
    )
