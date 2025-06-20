"""AWS Lambda adapter for Slack webhooks."""

from __future__ import annotations

import logging
import os
from typing import Any, Tuple

from mangum import Mangum
from slack_sdk.web.async_client import AsyncWebClient

from webhook.handler import WebhookHandler
from webhook.infrastructure.slack_api import SlackAPIRepository
from webhook.infrastructure.sqs_job_queue import SQSJobQueue
from webhook.infrastructure.slack_signature_validator import SlackSignatureValidator
from webhook.security.webhook_security_service import WebhookSecurityService

from .secrets_loader import AWSSecretsLoader

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global secrets loader
_secrets_loader = AWSSecretsLoader()


def create_webhook_handler() -> Tuple[WebhookHandler, WebhookSecurityService]:
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
    except Exception as e:  # noqa: BLE001
        logger.error(
            "Failed to load secrets, continuing with environment variables: %s",
            e,
        )


def _create_app() -> Any:
    from emojismith.presentation.web.slack_webhook_api import create_webhook_api
    from emojismith.application.create_webhook_app import create_webhook_app

    return create_webhook_api(create_webhook_app())


app = _create_app()
handler = Mangum(app)
