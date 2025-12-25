"""Structured JSON logging for observability."""

from __future__ import annotations

import json
import logging
import uuid
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

# Sentinel value used when no trace id has been set in the current context.
DEFAULT_TRACE_ID = "no-trace-id"

# Context variable for trace correlation across async boundaries
trace_id_var: ContextVar[str] = ContextVar("trace_id", default=DEFAULT_TRACE_ID)


def ensure_trace_id() -> str:
    """Ensure a real trace id is set in the current context and return it.

    If the current value is unset (empty) or the default sentinel, a new UUID is
    generated, stored in the ContextVar, and returned. Otherwise, the existing
    value is returned unchanged.
    """

    current = trace_id_var.get()
    if not current or current == DEFAULT_TRACE_ID:
        new_trace_id = str(uuid.uuid4())
        trace_id_var.set(new_trace_id)
        return new_trace_id

    return current


class JSONFormatter(logging.Formatter):
    """Formats log records as JSON for CloudWatch/Datadog/Logfire compatibility."""

    def format(self, record: logging.LogRecord) -> str:
        log_data: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "trace_id": trace_id_var.get(),
        }

        # Merge extra fields into root (for top-level searchability)
        if hasattr(record, "event_data") and isinstance(record.event_data, dict):
            log_data.update(record.event_data)

        # Include exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data, default=str)


def setup_logging(level: int = logging.INFO) -> None:
    """Configure root logger with JSON formatter."""
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Remove existing handlers to avoid duplicate logs
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    root_logger.addHandler(handler)


def log_event(
    logger: logging.Logger,
    level: int,
    message: str,
    *,
    exc_info: Any = None,
    **event_fields: Any,
) -> None:
    """Log a structured event with additional fields merged at root level.

    Example:
        log_event(
            logger,
            logging.INFO,
            "Prompt enhanced",
            event="prompt_enhancement",
            original_description="a cat",
            enhanced_prompt="A cute cartoon cat emoji...",
        )
    """
    logger.log(level, message, extra={"event_data": event_fields}, exc_info=exc_info)
