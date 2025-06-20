"""Application layer factory for the Slack webhook handler."""

from emojismith.application.handlers.slack_webhook_handler import (
    SlackEventProcessor,
    SlackWebhookHandler,
)
from emojismith.infrastructure.aws.webhook_handler import create_webhook_handler


def create_webhook_app() -> SlackWebhookHandler:
    """Construct the application-level Slack webhook handler."""
    webhook_handler, security_service = create_webhook_handler()
    event_processor = SlackEventProcessor(webhook_handler)
    return SlackWebhookHandler(security_service, event_processor)
