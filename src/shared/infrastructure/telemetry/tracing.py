"""OpenTelemetry tracing setup and helpers."""

from __future__ import annotations

import logging
from typing import cast

from opentelemetry import propagate, trace
from opentelemetry.propagators.textmap import TextMapPropagator
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SpanExporter
from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased

from shared.infrastructure.logging import ensure_trace_id
from shared.infrastructure.telemetry.config import TelemetryConfig

logger = logging.getLogger(__name__)


def create_tracing_provider(config: TelemetryConfig) -> TracingProvider:
    provider = TracingProvider(config=config)
    provider.configure()
    provider.instrument_http_clients()
    return provider


class TracingProvider:
    """Configures OpenTelemetry tracing and provides small helpers."""

    def __init__(self, *, config: TelemetryConfig) -> None:
        self._config = config
        self._configured = False

    @property
    def enabled(self) -> bool:
        return self._config.tracing_enabled

    def configure(self) -> None:
        """Configure global tracer provider + propagator (idempotent)."""
        if self._configured:
            return

        if not self._config.tracing_enabled:
            self._configured = True
            return

        base_resource = Resource.create(
            {
                "service.name": self._config.service_name,
                "deployment.environment": self._config.environment,
            }
        )
        # Use GCP resource detector to properly identify Cloud Run resources.
        resource = _get_gcp_resource(base_resource)
        sampler = ParentBased(TraceIdRatioBased(self._config.trace_sample_rate))
        tracer_provider = TracerProvider(resource=resource, sampler=sampler)

        exporter = _build_cloud_trace_exporter(self._config.project_id)
        if exporter is not None:
            tracer_provider.add_span_processor(BatchSpanProcessor(exporter))

        trace.set_tracer_provider(tracer_provider)

        propagator = _build_gcp_propagator()
        if propagator is not None:
            propagate.set_global_textmap(propagator)

        self._configured = True

    def instrument_http_clients(self) -> None:
        """Enable client auto-instrumentation (best effort)."""
        if not self._config.tracing_enabled:
            return

        try:
            from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

            HTTPXClientInstrumentor().instrument()
        except Exception:  # pragma: no cover - optional instrumentation
            logger.debug("HTTPX instrumentation unavailable", exc_info=True)

        try:
            from opentelemetry.instrumentation.aiohttp_client import (
                AioHttpClientInstrumentor,
            )

            AioHttpClientInstrumentor().instrument()
        except Exception:  # pragma: no cover - optional instrumentation
            logger.debug("aiohttp instrumentation unavailable", exc_info=True)

    def sync_trace_context(self) -> str:
        """Sync OTel trace context into shared trace_id ContextVar."""
        return ensure_trace_id()


def _build_cloud_trace_exporter(project_id: str) -> SpanExporter | None:
    if not project_id:
        # Avoid configuring Cloud exporters in local/dev/test environments.
        return None

    try:
        from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
    except Exception:  # pragma: no cover - dependency/import variation
        logger.debug("Cloud Trace exporter unavailable", exc_info=True)
        return None

    try:
        return cast(SpanExporter, CloudTraceSpanExporter(project_id=project_id))
    except TypeError:
        # Some versions infer project from environment/default credentials.
        return cast(SpanExporter, CloudTraceSpanExporter())


def _build_gcp_propagator() -> TextMapPropagator | None:
    try:
        from opentelemetry.propagators.cloud_trace_propagator import (
            CloudTraceFormatPropagator,
        )

        return cast(TextMapPropagator, CloudTraceFormatPropagator())
    except Exception:  # pragma: no cover - optional dependency
        return None


def _get_gcp_resource(base_resource: Resource) -> Resource:
    """Merge base resource with GCP-detected resource attributes."""
    try:
        from opentelemetry.resourcedetector.gcp_resource_detector import (
            GoogleCloudResourceDetector,
        )
        from opentelemetry.sdk.resources import get_aggregated_resources

        return get_aggregated_resources(
            [GoogleCloudResourceDetector(raise_on_error=False)],
            initial_resource=base_resource,
        )
    except Exception:  # pragma: no cover - optional dependency
        logger.debug("GCP resource detector unavailable", exc_info=True)
        return base_resource
