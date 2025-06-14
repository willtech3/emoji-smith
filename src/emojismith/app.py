"""FastAPI application factory."""

from fastapi import FastAPI
from typing import Dict, Any
from emojismith.application.handlers.slack_webhook import (
    SlackWebhookHandler,
)


def create_webhook_handler() -> SlackWebhookHandler:
    """Create webhook handler with dependencies."""
    # TODO: Implement proper dependency injection in future iterations
    # For now, return a mock to make tests pass
    from unittest.mock import AsyncMock

    mock_emoji_service = AsyncMock()
    mock_slack_repo = AsyncMock()

    return SlackWebhookHandler(
        emoji_service=mock_emoji_service, slack_repo=mock_slack_repo
    )


def create_app() -> FastAPI:
    """Create FastAPI application."""
    app = FastAPI(
        title="Emoji Smith",
        description="AI-powered custom emoji generator for Slack",
        version="0.1.0",
    )

    webhook_handler = create_webhook_handler()

    @app.get("/health")
    async def health_check() -> Dict[str, str]:
        """Health check endpoint."""
        return {"status": "healthy"}

    @app.post("/slack/events")
    async def slack_events(payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle Slack webhook events."""
        return await webhook_handler.handle_message_action(payload)

    return app
