"""AWS Lambda adapter for Slack webhooks."""

from __future__ import annotations

import logging
import os
import uuid
from typing import Any

import aioboto3
from fastapi import FastAPI, Request
from mangum import Mangum
from slack_sdk.web.async_client import AsyncWebClient

from emojismith.application.handlers.slack_webhook_handler import (
    SlackWebhookHandler,
    WebhookEventProcessor,
)
from emojismith.domain.services.webhook_security_service import WebhookSecurityService
from emojismith.infrastructure.jobs.sqs_job_queue import SQSJobQueue
from emojismith.infrastructure.security.slack_signature_validator import (
    SlackSignatureValidator,
)
from emojismith.infrastructure.slack.slack_api import SlackAPIRepository
from shared.infrastructure.logging import log_event, setup_logging, trace_id_var

try:
    # When deployed as Lambda package, secrets_loader is at root
    from secrets_loader import AWSSecretsLoader
except ImportError:
    # When running locally or in tests, use relative import
    from .secrets_loader import AWSSecretsLoader

# Configure structured JSON logging for Lambda CloudWatch
setup_logging()
logger = logging.getLogger(__name__)

# Global secrets loader
_secrets_loader = AWSSecretsLoader()


def create_webhook_handler() -> tuple[SlackWebhookHandler, WebhookSecurityService]:
    """Create webhook handler with minimal dependencies."""
    slack_token = os.getenv("SLACK_BOT_TOKEN")
    slack_signing_secret = os.getenv("SLACK_SIGNING_SECRET")
    queue_url = os.getenv("SQS_QUEUE_URL")

    if not slack_token:
        raise ValueError("SLACK_BOT_TOKEN environment variable is required")
    if not slack_signing_secret:
        raise ValueError("SLACK_SIGNING_SECRET environment variable is required")
    if not queue_url:
        raise ValueError("SQS_QUEUE_URL environment variable is required")

    slack_client = AsyncWebClient(token=slack_token)
    slack_repo = SlackAPIRepository(slack_client)
    # Use aioboto3-based SQS job queue from emojismith infrastructure
    session = aioboto3.Session()
    job_queue = SQSJobQueue(session=session, queue_url=queue_url)

    signature_validator = SlackSignatureValidator(signing_secret=slack_signing_secret)
    security_service = WebhookSecurityService(signature_validator)

    processor = WebhookEventProcessor(
        slack_repo=slack_repo,
        job_queue=job_queue,
        google_enabled=True,
    )
    slack_handler = SlackWebhookHandler(
        security_service=security_service, event_processor=processor
    )
    return slack_handler, security_service


if os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
    try:
        _secrets_loader.load_secrets()
    except Exception as e:
        logger.error(
            "Failed to load secrets, continuing with environment variables: %s",
            e,
        )


def _create_app() -> Any:
    """Create minimal FastAPI app for webhook handling."""
    app = FastAPI(
        title="Emoji Smith Webhook",
        description="Minimal webhook handler for Slack events",
        version="0.1.0",
    )

    # Create handler and security service
    webhook_handler, security_service = create_webhook_handler()

    @app.get("/health")
    async def health_check() -> dict:
        return {"status": "healthy", "service": "webhook"}

    @app.post("/slack/events")
    async def slack_events(request: Request) -> dict:
        # Generate and set trace ID for this request
        request_trace_id = str(uuid.uuid4())
        trace_id_var.set(request_trace_id)

        log_event(
            logger,
            logging.INFO,
            "Slack event received",
            event="webhook_received",
            endpoint="/slack/events",
        )

        body = await request.body()
        headers = dict(request.headers)
        return await webhook_handler.handle_event(body, headers)

    @app.post("/slack/interactive")
    async def slack_interactive(request: Request) -> dict:
        # Generate and set trace ID for this request
        request_trace_id = str(uuid.uuid4())
        trace_id_var.set(request_trace_id)

        log_event(
            logger,
            logging.INFO,
            "Slack interactive event received",
            event="webhook_received",
            endpoint="/slack/interactive",
        )

        body = await request.body()
        headers = dict(request.headers)
        return await webhook_handler.handle_event(body, headers)

    @app.post("/webhook")
    async def webhook_legacy(request: Request) -> dict:
        logger.info("Received request to legacy /webhook endpoint")
        # Forward to events endpoint
        return await slack_events(request)

    return app


# Lazy initialization pattern for Lambda
# This allows the module to be imported without requiring AWS credentials,
# which is needed for CI validation and testing
_app = None
_handler = None


def _get_app() -> Any:
    """Lazily create the FastAPI app on first use."""
    global _app
    if _app is None:
        _app = _create_app()
    return _app


def handler(event: dict, context: Any) -> dict:
    """Lambda handler with lazy initialization."""
    global _handler
    if _handler is None:
        _handler = Mangum(_get_app(), lifespan="off", api_gateway_base_path="/")
    return _handler(event, context)
