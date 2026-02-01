"""Cloud Run adapter for Slack webhooks.

This module intentionally constructs the production `app` at import time so Cloud
Run fails fast if required environment variables are missing.

For tests or embedding Emoji Smith into another FastAPI application, prefer
calling `create_app()` with an injected `SlackWebhookHandler`.
"""

import logging
import os
import time
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from slack_sdk.web.async_client import AsyncWebClient

from emojismith.application.handlers.slack_webhook_handler import (
    SlackWebhookHandler,
    WebhookEventProcessor,
)
from emojismith.domain.services.webhook_security_service import WebhookSecurityService
from emojismith.infrastructure.gcp.pubsub_job_queue import PubSubJobQueue
from emojismith.infrastructure.security.slack_signature_validator import (
    SlackSignatureValidator,
)
from emojismith.infrastructure.slack.slack_api import SlackAPIRepository
from shared.infrastructure.logging import (
    DEFAULT_TRACE_ID,
    log_event,
    setup_logging,
    trace_id_var,
)
from shared.infrastructure.telemetry import (
    TelemetryConfig,
    create_metrics_recorder,
    create_tracing_provider,
)

# Configure logging
setup_logging()
logger = logging.getLogger(__name__)


def create_webhook_handler() -> tuple[SlackWebhookHandler, WebhookSecurityService]:
    """Create webhook handler with dependencies."""
    slack_token = os.environ.get("SLACK_BOT_TOKEN")
    slack_signing_secret = os.environ.get("SLACK_SIGNING_SECRET")

    # PubSub config is read inside PubSubJobQueue from env PUBSUB_PROJECT
    # and PUBSUB_TOPIC

    if not slack_token:
        raise ValueError("SLACK_BOT_TOKEN environment variable is required")
    if not slack_signing_secret:
        raise ValueError("SLACK_SIGNING_SECRET environment variable is required")

    slack_client = AsyncWebClient(token=slack_token)
    slack_repo = SlackAPIRepository(slack_client)

    # Use PubSub job queue
    job_queue = PubSubJobQueue()

    signature_validator = SlackSignatureValidator(signing_secret=slack_signing_secret)
    security_service = WebhookSecurityService(signature_validator)

    processor = WebhookEventProcessor(
        slack_repo=slack_repo,
        job_queue=job_queue,
        google_enabled=True,
    )
    slack_handler = SlackWebhookHandler(
        security_service=security_service, event_processor=processor
    )
    return slack_handler, security_service


def create_app(*, webhook_handler: SlackWebhookHandler | None = None) -> FastAPI:
    """Create a FastAPI app for Slack webhooks.

    When `webhook_handler` is omitted, this function constructs production
    dependencies from environment variables.
    """
    if webhook_handler is None:
        webhook_handler, _security_service = create_webhook_handler()

    app = FastAPI(
        title="Emoji Smith Webhook",
        description="Cloud Run webhook handler for Slack events",
        version="0.1.0",
    )

    telemetry_config = TelemetryConfig.from_environment()
    tracing_provider = create_tracing_provider(telemetry_config)
    metrics_recorder = create_metrics_recorder(telemetry_config)

    if telemetry_config.tracing_enabled:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        if not getattr(app.state, "otel_instrumented", False):
            FastAPIInstrumentor.instrument_app(app)
            app.state.otel_instrumented = True

    @app.middleware("http")
    async def telemetry_middleware(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        token = trace_id_var.set(DEFAULT_TRACE_ID)
        start_time = time.monotonic()
        response: Response | None = None
        try:
            tracing_provider.sync_trace_context()
            response = await call_next(request)
            return response
        except Exception as exc:
            metrics_recorder.record_error(
                where="webhook",
                error_type=exc.__class__.__name__,
            )
            raise
        finally:
            duration_s = time.monotonic() - start_time
            status_code = response.status_code if response is not None else 500
            metrics_recorder.record_request(
                endpoint=request.url.path,
                method=request.method,
                status_code=status_code,
                duration_s=duration_s,
            )
            trace_id_var.reset(token)

    @app.get("/health")
    async def health_check() -> dict:
        return {"status": "healthy", "service": "webhook"}

    @app.post("/slack/events")
    async def slack_events(request: Request) -> dict:
        log_event(
            logger,
            logging.INFO,
            "Slack event received",
            event="webhook_received",
            endpoint="/slack/events",
        )
        body = await request.body()
        headers = dict(request.headers)
        return await webhook_handler.handle_event(body, headers)

    @app.post("/slack/interactive")
    async def slack_interactive(request: Request) -> dict:
        log_event(
            logger,
            logging.INFO,
            "Slack event received",
            event="webhook_received",
            endpoint="/slack/interactive",
        )
        body = await request.body()
        headers = dict(request.headers)
        return await webhook_handler.handle_event(body, headers)

    return app


app = create_app()
