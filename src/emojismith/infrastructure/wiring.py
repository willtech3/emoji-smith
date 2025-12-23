"""Infrastructure wiring for Slack webhook handling."""

from emojismith.application.handlers.slack_webhook_handler import SlackWebhookHandler
from emojismith.infrastructure.aws.webhook_handler import create_webhook_handler


def create_webhook_app() -> SlackWebhookHandler:
    """Create the SlackWebhookHandler with all dependencies."""
    slack_handler, _security_service = create_webhook_handler()
    return slack_handler
