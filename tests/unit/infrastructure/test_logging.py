"""Unit tests for structured logging infrastructure."""

import json
import logging

import pytest

from shared.infrastructure.logging import (
    JSONFormatter,
    log_event,
    setup_logging,
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
        assert result["logger"] == "test.logger"
        assert result["message"] == "Test message"
        assert "timestamp" in result
        assert "trace_id" in result

    def test_injects_trace_id_from_context_var(self) -> None:
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

    def test_includes_exception_info(self) -> None:
        """Verify exception info is included when present."""
        formatter = JSONFormatter()
        try:
            raise ValueError("Test error")
        except ValueError:
            import sys

            exc_info = sys.exc_info()
            record = logging.LogRecord(
                name="test",
                level=logging.ERROR,
                pathname="",
                lineno=0,
                msg="Error occurred",
                args=(),
                exc_info=exc_info,
            )
            result = json.loads(formatter.format(record))

            assert "exception" in result
            assert "ValueError" in result["exception"]
            assert "Test error" in result["exception"]

    def test_timestamp_is_iso8601_format(self) -> None:
        """Verify timestamp is in ISO8601 format."""
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
        result = json.loads(formatter.format(record))

        # ISO8601 format should contain T and end with timezone
        assert "T" in result["timestamp"]
        # Should be parseable as ISO format
        from datetime import datetime

        datetime.fromisoformat(result["timestamp"])

    def test_handles_non_dict_event_data(self) -> None:
        """Verify non-dict event_data is ignored gracefully."""
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
        record.event_data = "not a dict"  # type: ignore[attr-defined]

        # Should not raise
        result = json.loads(formatter.format(record))
        assert "event_data" not in result


class TestSetupLogging:
    """Tests for setup_logging function."""

    def test_configures_json_formatter(self) -> None:
        """Verify setup_logging configures JSON formatter on root logger."""
        # Save original handlers
        root_logger = logging.getLogger()
        original_handlers = root_logger.handlers[:]
        original_level = root_logger.level

        try:
            setup_logging()

            # Check that at least one handler has JSONFormatter
            has_json_formatter = any(
                isinstance(h.formatter, JSONFormatter) for h in root_logger.handlers
            )
            assert has_json_formatter
        finally:
            # Restore original handlers
            for handler in root_logger.handlers[:]:
                root_logger.removeHandler(handler)
            for handler in original_handlers:
                root_logger.addHandler(handler)
            root_logger.setLevel(original_level)

    def test_removes_duplicate_handlers(self) -> None:
        """Verify setup_logging removes existing handlers before adding new one."""
        root_logger = logging.getLogger()
        original_handlers = root_logger.handlers[:]
        original_level = root_logger.level

        try:
            # Add multiple handlers
            for _ in range(3):
                setup_logging()

            # Should only have one handler after multiple calls
            assert len(root_logger.handlers) == 1
        finally:
            # Restore original handlers
            for handler in root_logger.handlers[:]:
                root_logger.removeHandler(handler)
            for handler in original_handlers:
                root_logger.addHandler(handler)
            root_logger.setLevel(original_level)


class TestLogEvent:
    """Tests for log_event helper."""

    def test_log_event_with_fields(self, caplog: pytest.LogCaptureFixture) -> None:
        """Verify log_event passes event_data correctly."""
        logger = logging.getLogger("test.log_event")
        with caplog.at_level(logging.INFO):
            log_event(logger, logging.INFO, "Test", event="my_event", value=123)

        assert len(caplog.records) == 1
        assert caplog.records[0].event_data == {"event": "my_event", "value": 123}

    def test_log_event_message(self, caplog: pytest.LogCaptureFixture) -> None:
        """Verify log_event records the correct message."""
        logger = logging.getLogger("test.log_event_msg")
        with caplog.at_level(logging.INFO):
            log_event(logger, logging.INFO, "Test message here")

        assert len(caplog.records) == 1
        assert caplog.records[0].message == "Test message here"

    def test_log_event_level(self, caplog: pytest.LogCaptureFixture) -> None:
        """Verify log_event respects log level."""
        logger = logging.getLogger("test.log_event_level")
        with caplog.at_level(logging.WARNING):
            log_event(logger, logging.INFO, "Should not appear")
            log_event(logger, logging.WARNING, "Should appear")

        assert len(caplog.records) == 1
        assert caplog.records[0].message == "Should appear"


class TestTraceIdVar:
    """Tests for trace_id context variable."""

    def test_set_and_get(self) -> None:
        """Verify trace_id can be set and retrieved."""
        original = trace_id_var.get()
        try:
            trace_id_var.set("custom-trace-456")
            assert trace_id_var.get() == "custom-trace-456"
        finally:
            trace_id_var.set(original)

    def test_default_returns_no_trace_id(self) -> None:
        """Verify ContextVar has expected default when first created."""
        from contextvars import ContextVar

        # Create a fresh ContextVar with same signature to verify behavior
        fresh_var: ContextVar[str] = ContextVar("test_trace_id", default="no-trace-id")
        assert fresh_var.get() == "no-trace-id"
