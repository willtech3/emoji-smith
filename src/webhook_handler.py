"""AWS Lambda handler for webhook processing (package deployment)."""

import json
import logging
import os
import urllib.parse
from typing import Dict, Any

from fastapi import FastAPI, Request, HTTPException
from mangum import Mangum
from slack_sdk.web.async_client import AsyncWebClient

from webhook.handler import WebhookHandler
from webhook.infrastructure.slack_api import SlackAPIRepository
from webhook.infrastructure.sqs_job_queue import SQSJobQueue
from webhook.domain.webhook_request import WebhookRequest
from webhook.security.webhook_security_service import WebhookSecurityService
from webhook.infrastructure.slack_signature_validator import SlackSignatureValidator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_webhook_handler() -> tuple[WebhookHandler, WebhookSecurityService]:
    """Create webhook handler with minimal dependencies."""
    # Load environment variables
    slack_token = os.getenv("SLACK_BOT_TOKEN")
    slack_signing_secret = os.getenv("SLACK_SIGNING_SECRET")
    queue_url = os.getenv("SQS_QUEUE_URL")

    # Validate required environment variables
    if not slack_token:
        raise ValueError("SLACK_BOT_TOKEN environment variable is required")
    if not slack_signing_secret:
        raise ValueError("SLACK_SIGNING_SECRET environment variable is required")
    if not queue_url:
        raise ValueError("SQS_QUEUE_URL environment variable is required")

    # Create Slack client and repository
    slack_client = AsyncWebClient(token=slack_token)
    slack_repo = SlackAPIRepository(slack_client)

    # Create job queue
    job_queue = SQSJobQueue(queue_url=queue_url)

    # Create webhook security service
    signature_validator = SlackSignatureValidator(signing_secret=slack_signing_secret.encode('utf-8'))
    security_service = WebhookSecurityService(signature_validator)

    # Create webhook handler
    webhook_handler = WebhookHandler(slack_repo=slack_repo, job_queue=job_queue)

    return webhook_handler, security_service


def create_app() -> FastAPI:
    """Create FastAPI application for webhook processing."""
    app = FastAPI(
        title="Emoji Smith Webhook",
        description="Webhook handler for Slack emoji creation",
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
        result: Dict[str, Any] = await slack_events(request)
        return result

    return app


# Create the FastAPI app and Mangum handler for Lambda
app = create_app()
handler = Mangum(app)
