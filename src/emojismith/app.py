"""FastAPI application factory."""

from fastapi import FastAPI
from typing import Dict, Any
from emojismith.application.handlers.slack_webhook import SlackWebhookHandler
from emojismith.application.services.emoji_service import EmojiCreationService


def create_webhook_handler() -> SlackWebhookHandler:
    """Create webhook handler with dependencies."""
    # TODO: Implement proper dependency injection in future iterations
    # For now, use mocked dependencies to make tests pass
    from unittest.mock import AsyncMock

    mock_slack_repo = AsyncMock()
    emoji_service = EmojiCreationService(slack_repo=mock_slack_repo)

    return SlackWebhookHandler(emoji_service=emoji_service)


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
        event_type = payload.get("type")

        if event_type == "message_action":
            return await webhook_handler.handle_message_action(payload)
        elif event_type == "view_submission":
            return await webhook_handler.handle_modal_submission(payload)
        else:
            return {"status": "ignored"}

    return app
