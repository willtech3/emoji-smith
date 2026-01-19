"""Cloud Run adapter for Slack webhooks."""

import logging
import os

from fastapi import FastAPI, Request
from slack_sdk.web.async_client import AsyncWebClient

from emojismith.application.handlers.slack_webhook_handler import (
    SlackWebhookHandler,
    WebhookEventProcessor,
)
from emojismith.domain.services.webhook_security_service import WebhookSecurityService
from emojismith.infrastructure.gcp.pubsub_job_queue import PubSubJobQueue
from emojismith.infrastructure.security.slack_signature_validator import (
    SlackSignatureValidator,
)
from emojismith.infrastructure.slack.slack_api import SlackAPIRepository
from shared.infrastructure.logging import ensure_trace_id, log_event, setup_logging

# Configure logging
setup_logging()
logger = logging.getLogger(__name__)


def create_webhook_handler() -> tuple[SlackWebhookHandler, WebhookSecurityService]:
    """Create webhook handler with dependencies."""
    slack_token = os.environ.get("SLACK_BOT_TOKEN")
    slack_signing_secret = os.environ.get("SLACK_SIGNING_SECRET")

    # PubSub config is read inside PubSubJobQueue from env PUBSUB_PROJECT
    # and PUBSUB_TOPIC

    if not slack_token:
        raise ValueError("SLACK_BOT_TOKEN environment variable is required")
    if not slack_signing_secret:
        raise ValueError("SLACK_SIGNING_SECRET environment variable is required")

    slack_client = AsyncWebClient(token=slack_token)
    slack_repo = SlackAPIRepository(slack_client)

    # Use PubSub job queue
    job_queue = PubSubJobQueue()

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


app = FastAPI(
    title="Emoji Smith Webhook",
    description="Cloud Run webhook handler for Slack events",
    version="0.1.0",
)

# Create handler and security service
webhook_handler, _security_service = create_webhook_handler()


@app.get("/health")
async def health_check() -> dict:
    return {"status": "healthy", "service": "webhook"}


@app.post("/slack/events")
async def slack_events(request: Request) -> dict:
    ensure_trace_id()

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
    ensure_trace_id()
    log_event(
        logger,
        logging.INFO,
        "Slack event received",
        event="webhook_received",
        endpoint="/slack/interactive",
    )
    body = await request.body()
    headers = dict(request.headers)
    return await webhook_handler.handle_event(body, headers)
