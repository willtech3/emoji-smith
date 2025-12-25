"""Unit tests for structured logging infrastructure."""

import json
import logging

from shared.infrastructure.logging import (
    JSONFormatter,
    log_event,
    trace_id_var,
)


class TestJSONFormatter:
    """Tests for JSONFormatter."""

    def test_formats_standard_fields(self):
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
        assert result["logger"] == "test.logger"
        assert result["message"] == "Test message"
        assert "timestamp" in result
        assert "trace_id" in result

    def test_injects_trace_id_from_context_var(self):
        """Verify trace_id is injected from ContextVar."""
        formatter = JSONFormatter()
        trace_id_var.set("test-trace-123")

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

        assert result["trace_id"] == "test-trace-123"

    def test_merges_event_data_to_root(self):
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

    def test_log_event_with_fields(self, caplog):
        """Verify log_event passes event_data correctly."""
        logger = logging.getLogger("test.log_event")
        with caplog.at_level(logging.INFO):
            log_event(logger, logging.INFO, "Test", event="my_event", value=123)

        assert len(caplog.records) == 1
        assert caplog.records[0].event_data == {"event": "my_event", "value": 123}
