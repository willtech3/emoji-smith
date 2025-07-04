"""AWS Lambda adapter for Slack webhooks."""

from __future__ import annotations

import json
import logging
import os
import urllib.parse
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from mangum import Mangum
from slack_sdk.web.async_client import AsyncWebClient

from webhook.domain.webhook_request import WebhookRequest
from webhook.handler import WebhookHandler
from webhook.infrastructure.slack_api import SlackAPIRepository
from webhook.infrastructure.slack_signature_validator import SlackSignatureValidator
from webhook.infrastructure.sqs_job_queue import SQSJobQueue
from webhook.security.webhook_security_service import WebhookSecurityService

try:
    # When deployed as Lambda package, secrets_loader is at root
    from secrets_loader import AWSSecretsLoader  # type: ignore[import-not-found]
except ImportError:
    # When running locally or in tests, use relative import
    from .secrets_loader import AWSSecretsLoader

# Configure logging for Lambda CloudWatch
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)
# Also configure root logger for Lambda
logging.getLogger().setLevel(logging.INFO)

# Global secrets loader
_secrets_loader = AWSSecretsLoader()


def create_webhook_handler() -> tuple[WebhookHandler, WebhookSecurityService]:
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
    job_queue = SQSJobQueue(queue_url=queue_url)

    signature_validator = SlackSignatureValidator(
        signing_secret=slack_signing_secret.encode("utf-8")
    )
    security_service = WebhookSecurityService(signature_validator)

    webhook_handler = WebhookHandler(slack_repo=slack_repo, job_queue=job_queue)
    return webhook_handler, security_service


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
        logger.info("Received request to /slack/events")
        body = await request.body()
        headers = dict(request.headers)
        logger.info(f"Request headers: {headers}")
        logger.info(f"Request body length: {len(body)}")

        # Verify Slack signature
        timestamp = headers.get("x-slack-request-timestamp", "")
        signature = headers.get("x-slack-signature", "")

        webhook_request = WebhookRequest(
            body=body, timestamp=timestamp, signature=signature
        )

        if not security_service.is_authentic_webhook(webhook_request):
            raise HTTPException(status_code=401, detail="Invalid signature")

        # Parse payload
        try:
            payload = json.loads(body.decode("utf-8"))
            logger.info("Received JSON payload: %s", payload.get("type", "unknown"))
        except Exception:
            # Handle URL-encoded form data
            form_data = urllib.parse.parse_qs(body.decode("utf-8"))
            payload_str = form_data.get("payload", ["{}"])[0]
            payload = json.loads(payload_str)
            logger.info(
                "Received form-encoded payload: %s", payload.get("type", "unknown")
            )

        # Log full payload structure for debugging
        logger.info("Full payload keys: %s", list(payload.keys()))

        # Handle URL verification
        if payload.get("type") == "url_verification":
            logger.info("Handling URL verification challenge")
            return {"challenge": payload.get("challenge")}

        # Route to appropriate handler
        event_type = payload.get("type")
        logger.info("Processing event type: %s", event_type)

        if event_type == "message_action":
            logger.info("Handling message action")
            return await webhook_handler.handle_message_action(payload)
        elif event_type == "view_submission":
            logger.info("Handling view submission")
            return await webhook_handler.handle_modal_submission(payload)
        elif event_type == "block_actions":
            logger.info("Handling block actions")
            return await webhook_handler.handle_block_actions(payload)

        logger.warning("Unhandled event type: %s", event_type)
        return {"status": "ignored"}

    @app.post("/slack/interactive")
    async def slack_interactive(request: Request) -> dict:
        logger.info("Received request to /slack/interactive")
        # Same as events endpoint for interactive components
        return await slack_events(request)

    @app.post("/webhook")
    async def webhook_legacy(request: Request) -> dict:
        logger.info("Received request to legacy /webhook endpoint")
        # Forward to events endpoint
        return await slack_events(request)

    # Temporarily remove catch-all route - it's causing 422 errors
    # The catch-all route with path parameter is interfering with other routes
    # @app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
    # async def catch_all(request: Request, path: str) -> dict:
    #     logger.warning(f"Unhandled request to: /{path}")
    #     logger.warning(f"Method: {request.method}")
    #     logger.warning(f"Headers: {dict(request.headers)}")
    #     return {"error": f"Unhandled path: /{path}", "method": request.method}

    return app


app = _create_app()
handler = Mangum(app, lifespan="off", api_gateway_base_path="/")
