"""Application layer factory for creating the webhook FastAPI app."""

from fastapi import FastAPI

from emojismith.infrastructure.aws.webhook_handler import (
    create_app as create_infrastructure_app,
)


def create_webhook_app() -> FastAPI:
    """
    Create the webhook FastAPI application.

    This is the application layer entry point that should be used by
    presentation layer components (dev server, tests, etc).
    """
    # For now, delegate to the infrastructure implementation
    # In the future, this could orchestrate multiple infrastructure components
    return create_infrastructure_app()
