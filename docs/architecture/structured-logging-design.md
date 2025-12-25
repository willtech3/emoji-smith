# Structured Logging and Traceability Design

> **Status: IMPLEMENTED** — This is a fully-specified design document ready for implementation.
>
> **Legend:** ⬜ Not started | ✅ Completed

---

## 1. Shared Logging Infrastructure

Create a centralized logging module to ensure consistent JSON-structured logging across both Lambda functions.

### 1.1 Create Logging Module

**File:** `src/shared/infrastructure/logging.py` *(new file, create `infrastructure/` directory)*

#### ✅ 1.1.1 Create `src/shared/infrastructure/__init__.py`

```python
"""Shared infrastructure utilities."""
```

#### ✅ 1.1.2 Create `src/shared/infrastructure/logging.py`

```python
"""Structured JSON logging for observability."""

import json
import logging
from contextvars import ContextVar
from datetime import datetime, UTC
from typing import Any

# Context variable for trace correlation across async boundaries
trace_id_var: ContextVar[str] = ContextVar("trace_id", default="no-trace-id")


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


def log_event(logger: logging.Logger, level: int, message: str, **event_fields: Any) -> None:
    """Log a structured event with additional fields merged at root level.

    Example:
        log_event(logger, logging.INFO, "Prompt enhanced",
                  event="prompt_enhancement",
                  original_description="a cat",
                  enhanced_prompt="A cute cartoon cat emoji...")
    """
    logger.log(level, message, extra={"event_data": event_fields})
```

---

### 1.2 JSON Log Event Schema

All log events **MUST** include these fields:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `timestamp` | `string` (ISO8601) | ✅ | UTC timestamp |
| `level` | `string` | ✅ | Log level (INFO, WARNING, ERROR) |
| `logger` | `string` | ✅ | Logger name (module path) |
| `message` | `string` | ✅ | Human-readable message |
| `module` | `string` | ✅ | Python module name |
| `trace_id` | `string` | ✅ | UUID for request correlation |
| `event` | `string` | ⬜ Optional | Event type for filtering |
| `exception` | `string` | ⬜ Optional | Formatted traceback if error |

#### Defined Event Types

| `event` Value | Additional Fields |
|---------------|-------------------|
| `prompt_enhancement` | `original_description: str`, `enhanced_prompt: str` |
| `model_generation` | `provider: str`, `model: str`, `is_fallback: bool` |
| `job_received` | `job_id: str`, `user_id: str`, `image_provider: str` |
| `job_completed` | `job_id: str`, `duration_ms: int` |
| `job_failed` | `job_id: str`, `error: str` |

---

## 2. Domain Entity Update

#### ✅ 2.1 Add `trace_id` to `EmojiGenerationJob`

**File:** `src/shared/domain/entities/__init__.py`

Add the following changes to the `EmojiGenerationJob` dataclass:

```diff
@dataclass
class EmojiGenerationJob:
    """Domain entity representing an emoji generation job."""

    job_id: str
    user_description: str
    message_text: str
    user_id: str
    channel_id: str
    timestamp: str
    team_id: str
    emoji_name: str
    status: JobStatus
    sharing_preferences: EmojiSharingPreferences
    created_at: datetime
+   trace_id: str = ""  # For cross-Lambda tracing
    thread_ts: str | None = None
    # ... rest unchanged
```

#### ✅ 2.2 Update `create_new()` factory method

```diff
    @classmethod
    def create_new(
        cls,
        *,
        user_description: str,
        emoji_name: str,
        # ... existing params ...
+       trace_id: str = "",
    ) -> "EmojiGenerationJob":
        return cls(
            job_id=str(uuid.uuid4()),
+           trace_id=trace_id or str(uuid.uuid4()),  # Auto-generate if not provided
            # ... rest unchanged
        )
```

#### ✅ 2.3 Update `to_dict()` method

```diff
    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
+           "trace_id": self.trace_id,
            # ... rest unchanged
        }
```

#### ✅ 2.4 Update `from_dict()` method

```diff
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EmojiGenerationJob":
        return cls(
            job_id=data["job_id"],
+           trace_id=data.get("trace_id", ""),
            # ... rest unchanged
        )
```

---

## 3. Webhook Handler Instrumentation

**File:** `src/emojismith/infrastructure/aws/webhook_handler.py`

#### ✅ 3.1 Import logging utilities

```diff
+ import uuid
+ from shared.infrastructure.logging import setup_logging, trace_id_var, log_event

- logging.basicConfig(
-     level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
- )
+ setup_logging()
  logger = logging.getLogger(__name__)
```

#### ✅ 3.2 Set trace_id at request entry

In the `/slack/events` endpoint handler, set the trace context:

```python
@app.post("/slack/events")
async def slack_events(request: Request) -> dict:
    # Generate and set trace ID for this request
    request_trace_id = str(uuid.uuid4())
    trace_id_var.set(request_trace_id)

    log_event(logger, logging.INFO, "Slack event received",
              event="webhook_received",
              endpoint="/slack/events")

    body = await request.body()
    headers = dict(request.headers)
    return await webhook_handler.handle_event(body, headers)
```

#### ✅ 3.3 Pass trace_id when creating job

Update `WebhookEventProcessor` to pass trace_id:

**File:** `src/emojismith/application/handlers/slack_webhook_handler.py`

```diff
+ from shared.infrastructure.logging import trace_id_var

  job = EmojiGenerationJob.create_new(
      user_description=description,
      emoji_name=emoji_name,
+     trace_id=trace_id_var.get(),
      # ... rest unchanged
  )
```

---

## 4. Worker Handler Instrumentation

**File:** `src/emojismith/infrastructure/aws/worker_handler.py`

#### ✅ 4.1 Import and initialize logging

```diff
+ from shared.infrastructure.logging import setup_logging, trace_id_var, log_event

+ setup_logging()
  logger = logging.getLogger(__name__)
```

#### ✅ 4.2 Extract and set trace_id from job

```diff
  def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
      # ... secrets loading ...

      for record in event.get("Records", []):
          try:
              message_body = json.loads(record["body"])
              job = EmojiGenerationJob.from_dict(message_body)

+             # Set trace context from incoming job
+             trace_id_var.set(job.trace_id or job.job_id)
+
+             log_event(logger, logging.INFO, "Processing job",
+                       event="job_received",
+                       job_id=job.job_id,
+                       user_id=job.user_id,
+                       image_provider=job.image_provider)

              # ... processing ...
```

---

## 5. Application Layer Instrumentation

**File:** `src/emojismith/application/use_cases/build_prompt_use_case.py`

#### ✅ 5.1 Log prompt enhancement event

```diff
+ from shared.infrastructure.logging import log_event

  class BuildPromptUseCase:
      # ...

      async def build_prompt(self, spec: EmojiSpecification, ...) -> str:
          # ... after enhancement succeeds ...
          if enhance:
              try:
                  enhanced_prompt = await self._prompt_enhancer.enhance_prompt(
                      spec.context, base_prompt
                  )
+                 log_event(self._logger, logging.INFO, "Prompt enhanced",
+                           event="prompt_enhancement",
+                           original_description=spec.description,
+                           enhanced_prompt=enhanced_prompt[:200])  # Truncate for logs
                  return enhanced_prompt
```

---

## 6. Infrastructure Layer Instrumentation

### 6.1 OpenAI Provider

**File:** `src/emojismith/infrastructure/openai/openai_api.py`

#### ✅ 6.1.1 Log model generation

```diff
+ from shared.infrastructure.logging import log_event

  class OpenAIAPIRepository:
      # ... in generate_image method, after successful generation ...
+     log_event(self._logger, logging.INFO, "Image generated",
+               event="model_generation",
+               provider="openai",
+               model=self._model,
+               is_fallback=False)
```

### 6.2 Gemini Provider

**File:** `src/emojismith/infrastructure/google/gemini_api.py`

#### ✅ 6.2.1 Log Gemini generation

```diff
+ from shared.infrastructure.logging import log_event

  class GeminiAPIRepository:
      # ... in generate_image method, after successful generation ...
+     log_event(self._logger, logging.INFO, "Image generated",
+               event="model_generation",
+               provider="google_gemini",
+               model=self._model,
+               is_fallback=False)
```

#### ✅ 6.2.2 Log Imagen fallback

```diff
      # ... in imagen_generate_image or generate_with_fallback ...
+     log_event(self._logger, logging.INFO, "Image generated via Imagen",
+               event="model_generation",
+               provider="google_imagen",
+               model="imagen-4-ultra-preview",
+               is_fallback=True)
```

---

## 7. Testing Strategy

### 7.1 Unit Tests for Logging Module

#### ✅ 7.1.1 Create test file

**File:** `tests/unit/infrastructure/test_logging.py` *(new file)*

```python
"""Unit tests for structured logging infrastructure."""

import json
import logging
import pytest
from shared.infrastructure.logging import (
    JSONFormatter,
    setup_logging,
    trace_id_var,
    log_event,
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
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="msg", args=(), exc_info=None,
        )
        result = json.loads(formatter.format(record))

        assert result["trace_id"] == "test-trace-123"

    def test_merges_event_data_to_root(self):
        """Verify extra event_data fields are flattened to root."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="msg", args=(), exc_info=None,
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
```

### 7.2 Update Existing Tests

#### ✅ 7.2.1 Update `BuildPromptUseCase` tests

**File:** `tests/unit/application/use_cases/test_build_prompt_use_case.py`

Add assertion for `prompt_enhancement` log event:

```python
async def test_build_prompt_logs_enhancement_event(self, caplog):
    """Verify prompt enhancement is logged with correct event type."""
    # ... setup mock prompt_enhancer ...
    use_case = BuildPromptUseCase(prompt_enhancer=mock_enhancer)

    with caplog.at_level(logging.INFO):
        await use_case.build_prompt(spec, enhance=True)

    # Find the log record with event_data
    enhancement_logs = [
        r for r in caplog.records
        if hasattr(r, "event_data") and r.event_data.get("event") == "prompt_enhancement"
    ]
    assert len(enhancement_logs) == 1
    assert "original_description" in enhancement_logs[0].event_data
    assert "enhanced_prompt" in enhancement_logs[0].event_data
```

#### ✅ 7.2.2 Create `GeminiAPIRepository` tests

**File:** `tests/unit/infrastructure/google/test_gemini_api.py` *(new file)*

```python
"""Unit tests for GeminiAPIRepository logging."""

import logging
import pytest
from unittest.mock import AsyncMock, MagicMock


async def test_generate_image_logs_model_generation(caplog):
    """Verify model_generation event is logged on success."""
    # ... setup mock client ...
    with caplog.at_level(logging.INFO):
        await repo.generate_image("test prompt")

    generation_logs = [
        r for r in caplog.records
        if hasattr(r, "event_data") and r.event_data.get("event") == "model_generation"
    ]
    assert len(generation_logs) == 1
    assert generation_logs[0].event_data["provider"] == "google_gemini"
```

---

## 8. Implementation Checklist Summary

Copy this checklist to track progress:

```markdown
### Infrastructure Setup
- [x] 1.1.1 Create `src/shared/infrastructure/__init__.py`
- [x] 1.1.2 Create `src/shared/infrastructure/logging.py`

### Domain Entity
- [x] 2.1 Add `trace_id` field to `EmojiGenerationJob`
- [x] 2.2 Update `create_new()` method
- [x] 2.3 Update `to_dict()` method
- [x] 2.4 Update `from_dict()` method

### Webhook Handler
- [x] 3.1 Import logging utilities in webhook_handler.py
- [x] 3.2 Set trace_id at request entry
- [x] 3.3 Pass trace_id when creating job

### Worker Handler
- [x] 4.1 Import logging utilities in worker_handler.py
- [x] 4.2 Extract and set trace_id from job

### Application Layer
- [x] 5.1 Log prompt enhancement in BuildPromptUseCase

### Infrastructure Layer
- [x] 6.1.1 Log model generation in OpenAIAPIRepository
- [x] 6.2.1 Log Gemini generation in GeminiAPIRepository
- [x] 6.2.2 Log Imagen fallback

### Testing
- [x] 7.1.1 Create tests/unit/infrastructure/test_logging.py
- [x] 7.2.1 Add prompt_enhancement log assertion to BuildPromptUseCase tests
- [x] 7.2.2 Create tests/unit/infrastructure/google/test_gemini_api.py
```

---

## 9. Verification Commands

After implementation, run these to verify:

```bash
# Run all logging-related tests
pytest tests/unit/infrastructure/test_logging.py -v

# Run with coverage
pytest tests/unit/infrastructure/test_logging.py --cov=src/shared/infrastructure/logging

# Verify no import errors
python -c "from shared.infrastructure.logging import setup_logging, trace_id_var, log_event; print('OK')"
```
