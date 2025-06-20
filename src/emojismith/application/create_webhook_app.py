"""Application factory wiring dependencies for the webhook API."""

from __future__ import annotations

import logging
import os
from fastapi import FastAPI

from emojismith.infrastructure.aws.secrets_loader import AWSSecretsLoader
from emojismith.infrastructure.aws.webhook_dependencies import create_webhook_handler
from emojismith.application.handlers.slack_webhook_handler import SlackWebhookHandler
from emojismith.presentation.web.slack_webhook_api import create_webhook_api

logger = logging.getLogger(__name__)


def create_webhook_app() -> FastAPI:
    """Create the FastAPI application for Slack webhooks."""
    if os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
        try:
            AWSSecretsLoader().load_secrets()
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "Failed to load secrets, continuing with environment variables: %s",
                exc,
            )

    webhook_handler, security_service = create_webhook_handler()
    app_handler = SlackWebhookHandler(
        security_service=security_service, event_processor=webhook_handler
    )
    return create_webhook_api(app_handler)
