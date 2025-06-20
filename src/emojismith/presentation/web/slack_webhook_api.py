from __future__ import annotations

from typing import Any, Dict

from fastapi import FastAPI, Request

from emojismith.application.handlers.slack_webhook_handler import SlackWebhookHandler


def create_webhook_api(webhook_handler: SlackWebhookHandler) -> FastAPI:
    """Create FastAPI app for Slack webhooks."""
    app = FastAPI(title="Emoji Smith Webhook", version="0.1.0")

    @app.get("/health")
    async def health_check() -> Dict[str, str]:
        return webhook_handler.health_check()

    @app.post("/slack/events")
    async def slack_events(request: Request) -> Dict[str, Any]:
        body = await request.body()
        headers = dict(request.headers)
        return await webhook_handler.handle_event(body, headers)

    return app
