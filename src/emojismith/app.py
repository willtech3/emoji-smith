"""FastAPI application factory."""

import os
from dotenv import load_dotenv

from fastapi import FastAPI
from typing import Dict, Any, Optional
from slack_sdk.web.async_client import AsyncWebClient
from emojismith.application.handlers.slack_webhook import SlackWebhookHandler
from emojismith.application.services.emoji_service import EmojiCreationService
from emojismith.infrastructure.slack.slack_api import SlackAPIRepository
from emojismith.infrastructure.openai.openai_api import OpenAIAPIRepository
from emojismith.infrastructure.image.processing import PillowImageProcessor
from emojismith.domain.services.generation_service import EmojiGenerationService
from emojismith.domain.repositories.job_queue_repository import JobQueueRepository
from openai import AsyncOpenAI


def create_webhook_handler() -> SlackWebhookHandler:
    """Create webhook handler with dependencies."""
    # Load environment variables and initialize real Slack repository and service
    load_dotenv()
    slack_token = os.getenv("SLACK_BOT_TOKEN")
    slack_client = AsyncWebClient(token=slack_token)
    slack_repo = SlackAPIRepository(slack_client)

    openai_api_key = os.getenv("OPENAI_API_KEY")
    openai_client = AsyncOpenAI(api_key=openai_api_key)
    prompt_model = os.getenv("OPENAI_PROMPT_MODEL", "o3")
    fallback_models_env = os.getenv("OPENAI_FALLBACK_MODELS")
    fallback_models = (
        [m.strip() for m in fallback_models_env.split(",") if m.strip()]
        if fallback_models_env
        else ["gpt-4", "gpt-3.5-turbo"]
    )
    openai_repo = OpenAIAPIRepository(
        openai_client, model=prompt_model, fallback_models=fallback_models
    )
    image_processor = PillowImageProcessor()
    generator = EmojiGenerationService(
        openai_repo=openai_repo, image_processor=image_processor
    )

    # Configure job queue based on environment
    job_queue: Optional[JobQueueRepository] = None
    if os.getenv("AWS_LAMBDA_FUNCTION_NAME"):
        # Running in Lambda - configure SQS job queue
        job_queue = _create_sqs_job_queue()

    emoji_service = EmojiCreationService(
        slack_repo=slack_repo, emoji_generator=generator, job_queue=job_queue
    )

    return SlackWebhookHandler(emoji_service=emoji_service)


def _create_sqs_job_queue() -> JobQueueRepository:
    """Create SQS job queue for Lambda environment."""
    try:
        import aioboto3  # type: ignore[import-not-found]
        from emojismith.infrastructure.jobs.sqs_job_queue import SQSJobQueue

        session = aioboto3.Session()
        sqs_client = session.client("sqs")
        queue_url = os.getenv("SQS_QUEUE_URL")

        if not queue_url:
            raise ValueError(
                "SQS_QUEUE_URL environment variable is required for Lambda"
            )

        return SQSJobQueue(sqs_client=sqs_client, queue_url=queue_url)
    except ImportError:
        raise RuntimeError(
            "aioboto3 is required for SQS job queue in Lambda environment"
        )


def create_app() -> FastAPI:
    """Create FastAPI application."""
    app = FastAPI(
        title="Emoji Smith",
        description="AI-powered custom emoji generator for Slack",
        version="0.1.0",
    )

    webhook_handler = create_webhook_handler()

    @app.get("/health")
    async def health_check() -> Dict[str, str]:
        """Health check endpoint."""
        return {"status": "healthy"}

    @app.post("/slack/events")
    async def slack_events(payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle Slack webhook events, including URL verification."""
        # Handle Slack URL verification challenge
        if payload.get("type") == "url_verification":
            return {"challenge": payload.get("challenge")}

        event_type = payload.get("type")
        if event_type == "message_action":
            return await webhook_handler.handle_message_action(payload)
        if event_type == "view_submission":
            return await webhook_handler.handle_modal_submission(payload)
        return {"status": "ignored"}

    return app
