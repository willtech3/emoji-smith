"""Unit tests for TracingProvider."""

from __future__ import annotations

import re

from opentelemetry import trace

from shared.infrastructure.logging import DEFAULT_TRACE_ID, trace_id_var
from shared.infrastructure.telemetry.config import TelemetryConfig
from shared.infrastructure.telemetry.tracing import TracingProvider


def test_sync_trace_context_sets_trace_id_from_current_span() -> None:
    config = TelemetryConfig(
        project_id="",
        service_name="emoji-smith",
        environment="test",
        trace_sample_rate=1.0,
        metrics_enabled=False,
        tracing_enabled=True,
    )
    provider = TracingProvider(config=config)
    provider.configure()

    tracer = trace.get_tracer(__name__)
    token = trace_id_var.set(DEFAULT_TRACE_ID)
    try:
        with tracer.start_as_current_span("test-span") as span:
            provider.sync_trace_context()
            expected = format(span.get_span_context().trace_id, "032x")
            assert trace_id_var.get() == expected
            assert re.fullmatch(r"[0-9a-f]{32}", trace_id_var.get())
    finally:
        trace_id_var.reset(token)


def test_tracing_provider_noops_when_disabled() -> None:
    config = TelemetryConfig(
        project_id="",
        service_name="emoji-smith",
        environment="test",
        trace_sample_rate=1.0,
        metrics_enabled=False,
        tracing_enabled=False,
    )
    provider = TracingProvider(config=config)
    provider.configure()
    provider.instrument_http_clients()
    provider.sync_trace_context()
