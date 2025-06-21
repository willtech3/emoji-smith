"""Application layer factory for Slack webhook handling."""

from emojismith.application.handlers.slack_webhook_handler import (
    SlackWebhookHandler,
    WebhookEventProcessor,
)
from emojismith.infrastructure.aws.webhook_handler import create_webhook_handler


def create_webhook_app() -> SlackWebhookHandler:
    """Create the SlackWebhookHandler with all dependencies."""
    webhook_handler, security_service = create_webhook_handler()
    processor = WebhookEventProcessor(webhook_handler)
    return SlackWebhookHandler(security_service, processor)
