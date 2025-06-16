"""FastAPI application factory."""

import os
from dotenv import load_dotenv

from fastapi import FastAPI, Request, HTTPException
from typing import Dict, Any, Optional
import json
import urllib.parse
from slack_sdk.web.async_client import AsyncWebClient
from emojismith.application.handlers.slack_webhook import SlackWebhookHandler
from emojismith.application.services.emoji_service import EmojiCreationService
from emojismith.infrastructure.slack.slack_api import SlackAPIRepository
from emojismith.infrastructure.openai.openai_api import OpenAIAPIRepository
from emojismith.infrastructure.image.processing import PillowImageProcessor
from emojismith.infrastructure.image.pil_image_validator import PILImageValidator
from emojismith.domain.services.generation_service import EmojiGenerationService
from emojismith.domain.services.emoji_validation_service import EmojiValidationService
from emojismith.domain.repositories.job_queue_repository import JobQueueRepository
from emojismith.domain.services.webhook_security_service import WebhookSecurityService
from emojismith.domain.value_objects.webhook_request import WebhookRequest
from emojismith.infrastructure.security.slack_signature_validator import (
    SlackSignatureValidator,
)
from openai import AsyncOpenAI


def create_webhook_handler() -> tuple[SlackWebhookHandler, WebhookSecurityService]:
    """Create webhook handler with dependencies."""
    # Load environment variables and initialize real Slack repository and service
    load_dotenv()
    slack_token = os.getenv("SLACK_BOT_TOKEN")
    slack_signing_secret = os.getenv("SLACK_SIGNING_SECRET")
    openai_api_key = os.getenv("OPENAI_API_KEY")

    # Validate all required environment variables
    if not slack_token:
        raise ValueError("SLACK_BOT_TOKEN environment variable is required")
    if not slack_signing_secret:
        raise ValueError("SLACK_SIGNING_SECRET environment variable is required")
    if not openai_api_key:
        raise ValueError("OPENAI_API_KEY environment variable is required")

    slack_client = AsyncWebClient(token=slack_token)
    slack_repo = SlackAPIRepository(slack_client)

    openai_client = AsyncOpenAI(api_key=openai_api_key)
    chat_model = os.getenv("OPENAI_CHAT_MODEL", "o3")
    openai_repo = OpenAIAPIRepository(openai_client, model=chat_model)
    image_processor = PillowImageProcessor()

    # Create validation service with image validator
    image_validator = PILImageValidator()
    emoji_validation_service = EmojiValidationService(image_validator)

    generator = EmojiGenerationService(
        openai_repo=openai_repo,
        image_processor=image_processor,
        emoji_validator=emoji_validation_service,
    )

    # Configure job queue based on environment
    job_queue: Optional[JobQueueRepository] = None
    if os.getenv("AWS_LAMBDA_FUNCTION_NAME"):
        # Running in Lambda - configure SQS job queue
        job_queue = _create_sqs_job_queue()

    # Create file sharing repository
    from emojismith.infrastructure.slack.slack_file_sharing import (
        SlackFileSharingRepository,
    )

    file_sharing_repo = SlackFileSharingRepository(slack_client)

    emoji_service = EmojiCreationService(
        slack_repo=slack_repo,
        emoji_generator=generator,
        job_queue=job_queue,
        file_sharing_repo=file_sharing_repo,
    )

    # Create webhook security service
    signature_validator = SlackSignatureValidator(signing_secret=slack_signing_secret)
    security_service = WebhookSecurityService(signature_validator)

    return SlackWebhookHandler(emoji_service=emoji_service), security_service


def _create_sqs_job_queue() -> JobQueueRepository:
    """Create SQS job queue for Lambda environment."""
    try:
        import aioboto3  # type: ignore[import-untyped]
        from emojismith.infrastructure.jobs.sqs_job_queue import SQSJobQueue

        session = aioboto3.Session()
        queue_url = os.getenv("SQS_QUEUE_URL")

        if not queue_url:
            raise ValueError(
                "SQS_QUEUE_URL environment variable is required for Lambda"
            )

        return SQSJobQueue(session=session, queue_url=queue_url)
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

    webhook_handler, security_service = create_webhook_handler()

    @app.get("/health")
    async def health_check() -> Dict[str, str]:
        """Health check endpoint."""
        return {"status": "healthy"}

    @app.post("/slack/events")
    async def slack_events(request: Request) -> Dict[str, Any]:
        """Handle Slack webhook events with security and form data parsing."""
        # Get raw body and headers for security validation
        body = await request.body()
        timestamp = request.headers.get("X-Slack-Request-Timestamp")
        signature = request.headers.get("X-Slack-Signature")

        # Create webhook request for security validation
        webhook_request = WebhookRequest(
            body=body, timestamp=timestamp, signature=signature
        )

        # Validate webhook authenticity (skip for URL verification)
        if not body.startswith(b'{"type":"url_verification"'):
            if not security_service.is_authentic_webhook(webhook_request):
                raise HTTPException(status_code=401, detail="Invalid webhook signature")

        # Parse payload based on content type
        content_type = request.headers.get("content-type", "")

        if "application/x-www-form-urlencoded" in content_type:
            # Slack interactive components send form data
            # Parse form data from raw body since we already consumed it for security
            form_data = urllib.parse.parse_qs(body.decode("utf-8"))
            payload_str = form_data.get("payload", ["{}"])[0]
            payload = json.loads(payload_str)
        elif "application/json" in content_type:
            # Events API sends JSON
            payload = json.loads(body.decode("utf-8"))
        else:
            # Try JSON first, fallback to form
            try:
                payload = json.loads(body.decode("utf-8"))
            except Exception:
                form_data = urllib.parse.parse_qs(body.decode("utf-8"))
                payload_str = form_data.get("payload", ["{}"])[0]
                payload = json.loads(payload_str)

        # Handle Slack URL verification challenge
        if payload.get("type") == "url_verification":
            return {"challenge": payload.get("challenge")}

        event_type = payload.get("type")
        if event_type == "message_action":
            return await webhook_handler.handle_message_action(payload)
        if event_type == "view_submission":
            return await webhook_handler.handle_modal_submission(payload)
        return {"status": "ignored"}

    @app.post("/slack/interactive")
    async def slack_interactive(request: Request) -> Dict[str, Any]:
        """Handle Slack interactive components (modals, buttons, etc.)."""
        # Use the same logic as slack_events since interactive components
        # are just a subset of Slack webhook events
        return await slack_events(request)

    return app
