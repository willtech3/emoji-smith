from __future__ import annotations

import os
from typing import Tuple

from slack_sdk.web.async_client import AsyncWebClient

from webhook.handler import WebhookHandler
from webhook.infrastructure.slack_api import SlackAPIRepository
from webhook.infrastructure.sqs_job_queue import SQSJobQueue
from webhook.security.webhook_security_service import WebhookSecurityService
from webhook.infrastructure.slack_signature_validator import SlackSignatureValidator


def create_webhook_handler() -> Tuple[WebhookHandler, WebhookSecurityService]:
    """Create webhook handler and security service using environment config."""
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
