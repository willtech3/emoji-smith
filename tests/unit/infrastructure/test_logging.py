"""Unit tests for structured logging infrastructure."""

from __future__ import annotations

import json
import logging
import uuid

import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider as SdkTracerProvider

from shared.infrastructure.logging import (
    DEFAULT_TRACE_ID,
    JSONFormatter,
    ensure_trace_id,
    log_event,
    trace_id_var,
)


class TestJSONFormatter:
    """Tests for JSONFormatter."""

    def test_formats_standard_fields(self) -> None:
        """Verify standard fields are present in JSON output."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        result = json.loads(formatter.format(record))

        assert result["level"] == "INFO"
        assert result["severity"] == "INFO"
        assert result["logger"] == "test.logger"
        assert result["message"] == "Test message"
        assert result["module"] == "test"
        assert "timestamp" in result
        assert "trace_id" in result

    def test_injects_trace_id_from_context_var(self) -> None:
        """Verify trace_id is injected from ContextVar."""
        formatter = JSONFormatter()
        token = trace_id_var.set("test-trace-123")
        try:
            record = logging.LogRecord(
                name="test",
                level=logging.INFO,
                pathname="",
                lineno=0,
                msg="msg",
                args=(),
                exc_info=None,
            )
            result = json.loads(formatter.format(record))
        finally:
            trace_id_var.reset(token)

        assert result["trace_id"] == "test-trace-123"

    def test_merges_event_data_to_root(self) -> None:
        """Verify extra event_data fields are flattened to root."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="msg",
            args=(),
            exc_info=None,
        )
        record.event_data = {"event": "test_event", "custom_field": 42}

        result = json.loads(formatter.format(record))

        assert result["event"] == "test_event"
        assert result["custom_field"] == 42


class TestLogEvent:
    """Tests for log_event helper."""

    def test_log_event_with_fields(self, caplog) -> None:
        """Verify log_event passes event_data correctly."""
        logger = logging.getLogger("test.log_event")
        with caplog.at_level(logging.INFO):
            log_event(logger, logging.INFO, "Test", event="my_event", value=123)

        assert len(caplog.records) == 1
        assert caplog.records[0].event_data == {"event": "my_event", "value": 123}


class TestTraceIdHelpers:
    """Tests for trace_id helper behavior."""

    def test_ensure_trace_id_generates_uuid_when_default(self) -> None:
        """ensure_trace_id should generate and set a UUID when trace_id is unset."""
        token = trace_id_var.set("no-trace-id")
        try:
            trace_id = ensure_trace_id()
            assert trace_id != "no-trace-id"
            uuid.UUID(trace_id)
            assert trace_id_var.get() == trace_id
        finally:
            trace_id_var.reset(token)

    def test_ensure_trace_id_reuses_existing_value(self) -> None:
        """ensure_trace_id should return existing trace id if already set."""
        token = trace_id_var.set("trace-existing-123")
        try:
            assert ensure_trace_id() == "trace-existing-123"
        finally:
            trace_id_var.reset(token)


class TestCloudLoggingTraceCorrelation:
    """Tests for Cloud Logging trace correlation fields."""

    def test_formatter_includes_cloud_trace_fields_when_span_present(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "test-project")

        if not isinstance(trace.get_tracer_provider(), SdkTracerProvider):
            trace.set_tracer_provider(SdkTracerProvider())

        tracer = trace.get_tracer(__name__)
        formatter = JSONFormatter()

        token = trace_id_var.set(DEFAULT_TRACE_ID)
        try:
            with tracer.start_as_current_span("span"):
                trace_id = ensure_trace_id()
                record = logging.LogRecord(
                    name="test",
                    level=logging.INFO,
                    pathname="",
                    lineno=0,
                    msg="msg",
                    args=(),
                    exc_info=None,
                )
                result = json.loads(formatter.format(record))
        finally:
            trace_id_var.reset(token)

        assert result["trace_id"] == trace_id
        assert result["logging.googleapis.com/trace"] == (
            f"projects/test-project/traces/{trace_id}"
        )
        assert "logging.googleapis.com/spanId" in result
        assert isinstance(result["logging.googleapis.com/trace_sampled"], bool)
