"""Cloud Run worker application for processing Pub/Sub push messages."""

import base64
import json
import logging
import re
import time
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, HTTPException, Request, Response

from emojismith.app import create_worker_emoji_service
from shared.domain.dtos import EmojiGenerationJobDto
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

setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI()

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
        response = await call_next(request)
        return response
    except Exception as exc:
        metrics_recorder.record_error(where="worker", error_type=exc.__class__.__name__)
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
async def health() -> dict:
    """Health check endpoint."""
    return {"status": "healthy"}


@app.post("/pubsub")
async def process_pubsub_message(request: Request) -> dict:
    """
    Handle Pub/Sub push messages.
    """
    job_start_time: float | None = None
    job_provider = "unknown"
    try:
        envelope = await request.json()

        if not envelope or "message" not in envelope:
            raise HTTPException(
                status_code=400, detail="Invalid Pub/Sub message format"
            )

        message = envelope["message"]
        message_id = message.get("messageId", "unknown")

        # Decode the job data
        if "data" not in message:
            raise HTTPException(status_code=400, detail="Missing message data")

        job_data = base64.b64decode(message["data"]).decode("utf-8")
        job_dict = json.loads(job_data)

        job = EmojiGenerationJobDto(**job_dict)
        job_provider = job.image_provider

        trace_id_value = job.trace_id or job.job_id

        # Prefer continuing the trace (when the incoming job trace id is a valid
        # 32-hex OpenTelemetry trace id). Otherwise, fall back to using the job
        # trace id for log correlation only.
        job_trace_id = (job.trace_id or "").lower()
        use_otel_trace = telemetry_config.tracing_enabled and bool(
            re.fullmatch(r"[0-9a-f]{32}", job_trace_id)
        )

        job_start_time = time.monotonic()
        if use_otel_trace:
            from opentelemetry import trace
            from opentelemetry.context import Context
            from opentelemetry.sdk.trace.sampling import Decision, TraceIdRatioBased
            from opentelemetry.trace import (
                NonRecordingSpan,
                SpanContext,
                TraceFlags,
                TraceState,
                set_span_in_context,
            )

            sampling_result = TraceIdRatioBased(
                telemetry_config.trace_sample_rate
            ).should_sample(
                parent_context=Context(),
                trace_id=int(job_trace_id, 16),
                name="process_emoji_job",
                kind=trace.SpanKind.INTERNAL,
                attributes={},
                links=[],
            )
            sampled = sampling_result.decision is Decision.RECORD_AND_SAMPLE

            parent_context = set_span_in_context(
                NonRecordingSpan(
                    SpanContext(
                        trace_id=int(job_trace_id, 16),
                        span_id=0x01,
                        is_remote=True,
                        trace_flags=TraceFlags(1 if sampled else 0),
                        trace_state=TraceState(),
                    )
                )
            )
            tracer = trace.get_tracer(__name__)
            with tracer.start_as_current_span(
                "process_emoji_job",
                context=parent_context,
                attributes={
                    "job.id": job.job_id,
                    "job.provider": job.image_provider,
                    "pubsub.message_id": message_id,
                },
            ):
                tracing_provider.sync_trace_context()
                log_event(
                    logger,
                    logging.INFO,
                    "Processing job from Pub/Sub",
                    event="job_received",
                    job_id=job.job_id,
                    user_id=job.user_id,
                    image_provider=job.image_provider,
                    message_id=message_id,
                )

                emoji_service = create_worker_emoji_service(
                    metrics_recorder=metrics_recorder
                )
                await emoji_service.process_emoji_generation_job(job)
        else:
            trace_id_var.set(trace_id_value)
            log_event(
                logger,
                logging.INFO,
                "Processing job from Pub/Sub",
                event="job_received",
                job_id=job.job_id,
                user_id=job.user_id,
                image_provider=job.image_provider,
                message_id=message_id,
            )

            emoji_service = create_worker_emoji_service(
                metrics_recorder=metrics_recorder
            )
            await emoji_service.process_emoji_generation_job(job)

        duration_s = time.monotonic() - job_start_time
        duration_ms = int(duration_s * 1000)

        log_event(
            logger,
            logging.INFO,
            "Job completed",
            event="job_completed",
            job_id=job.job_id,
            duration_ms=duration_ms,
        )

        metrics_recorder.record_job_processed(
            status="ok",
            provider=job.image_provider,
            duration_s=duration_s,
        )

        return {"status": "ok", "messageId": message_id}

    except HTTPException:
        # Preserve client-facing 4xx errors (do not convert them to 5xx retries).
        raise
    except Exception as e:
        logger.exception("Error processing Pub/Sub message: %s", e)
        duration_s = time.monotonic() - job_start_time if job_start_time else 0.0
        metrics_recorder.record_job_processed(
            status="error",
            provider=job_provider,
            duration_s=duration_s,
        )
        metrics_recorder.record_error(
            where="worker",
            error_type=e.__class__.__name__,
        )
        # Return 500 to trigger Pub/Sub retry.
        raise HTTPException(status_code=500, detail="Internal error") from e
