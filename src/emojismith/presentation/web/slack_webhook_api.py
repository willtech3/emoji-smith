from __future__ import annotations

from fastapi import FastAPI, Request

from emojismith.application.handlers.slack_webhook_handler import SlackWebhookHandler


def create_webhook_api(webhook_handler: SlackWebhookHandler) -> FastAPI:
    """Create FastAPI application exposing Slack webhook endpoints."""
    app = FastAPI(
        title="Emoji Smith Webhook",
        description="Webhook handler for Slack emoji creation",
        version="0.1.0",
    )

    @app.get("/health")
    async def health_check() -> dict:
        return await webhook_handler.health_check()

    @app.post("/slack/events")
    async def slack_events(request: Request) -> dict:
        body = await request.body()
        headers = dict(request.headers)
        return await webhook_handler.handle_event(body, headers)

    @app.post("/slack/interactive")
    async def slack_interactive(request: Request) -> dict:
        body = await request.body()
        headers = dict(request.headers)
        return await webhook_handler.handle_event(body, headers)

    return app
