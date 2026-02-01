# GCP Observability Implementation Plan for Emoji Smith

> **Status: IMPLEMENTED (2026-02-01)** — OpenTelemetry tracing + metrics, Cloud Logging trace correlation, and Terraform IAM/API updates are implemented in the codebase.

## Overview

Implement comprehensive GCP observability (metrics, traces, structured logs) using OpenTelemetry with in-process exporters to Cloud Monitoring and Cloud Trace. The solution integrates with existing logging infrastructure and follows the codebase's DI patterns and layer separation.

---

## Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Export Method** | In-process OTLP exporters | Cloud Run has native OTel support; sidecars add cold start latency (critical for <3s webhook response) |
| **Metrics** | OTel → Cloud Monitoring | Vendor-portable, Google-recommended |
| **Tracing** | OTel → Cloud Trace | Standard approach, auto-correlates with Cloud Logging |
| **Log Correlation** | Cloud Logging special fields | Enables clicking from logs → traces in GCP Console |
| **Abstraction** | Infrastructure layer only | Domain stays pure; no observability protocols needed |

---

## Dependencies to Add

```toml
# pyproject.toml additions
"opentelemetry-api>=1.27.0",
"opentelemetry-sdk>=1.27.0",
"opentelemetry-exporter-gcp-trace>=1.9.0",
"opentelemetry-exporter-gcp-monitoring>=1.9.0",
"opentelemetry-instrumentation-fastapi>=0.48b0",
"opentelemetry-instrumentation-httpx>=0.48b0",
"opentelemetry-instrumentation-aiohttp-client>=0.48b0",
"opentelemetry-propagator-gcp>=1.9.0",
```

**Auto-instrumentation coverage:**
- `FastAPIInstrumentor` - traces all incoming HTTP requests
- `HTTPXClientInstrumentor` - traces OpenAI SDK calls (uses httpx)
- `AioHttpClientInstrumentor` - traces Slack SDK and other aiohttp calls

---

## Files to Create

### 1. Telemetry Module Structure
```
src/shared/infrastructure/telemetry/
├── __init__.py           # Exports public API
├── config.py             # TelemetryConfig dataclass
├── tracing.py            # TracingProvider class
└── metrics.py            # MetricsRecorder class
```

### 2. `config.py` - Configuration
- `TelemetryConfig` frozen dataclass with: `project_id`, `service_name`, `environment`, `trace_sample_rate`, `metrics_enabled`, `tracing_enabled`
- Factory method `from_environment()` reads from env vars (`GOOGLE_CLOUD_PROJECT`, `K_SERVICE`, `TRACE_SAMPLE_RATE`, etc.)

### 3. `tracing.py` - Tracing Provider
- `TracingProvider` class wrapping OTel SDK setup
- Creates `TracerProvider` with Cloud Trace exporter
- `sync_trace_context()` method bridges OTel context with existing `trace_id_var`
- Sets `CloudTraceFormatPropagator` for GCP trace context
- `instrument_http_clients()` method applies auto-instrumentation to httpx and aiohttp

### 4. `metrics.py` - Metrics Recorder
- `MetricsRecorder` class with OTel instruments:
  - **Counters**: `http_requests_total`, `jobs_total`, `emojis_generated_total`, `errors_total`
  - **Histograms**: `http_request_duration_seconds`, `job_duration_seconds`, `image_generation_duration_seconds`
- Methods: `record_request()`, `record_job_processed()`, `record_emoji_generated()`, `record_error()`

---

## Files to Modify

### 1. `src/shared/infrastructure/logging.py`

**Changes:**
- Add `severity` field (Cloud Logging uses this, not `level`)
- Add `get_cloud_logging_trace_fields()` function returning:
  - `logging.googleapis.com/trace` (full trace path)
  - `logging.googleapis.com/spanId`
  - `logging.googleapis.com/trace_sampled`
- Update `ensure_trace_id()` to check OTel context first, then fall back to UUID generation
- Update `JSONFormatter.format()` to include Cloud Logging fields

### 2. `src/emojismith/infrastructure/gcp/webhook_app.py`

**Changes:**
- Import and initialize `TelemetryConfig`, `create_tracing_provider()`, `create_metrics_recorder()`
- Add `FastAPIInstrumentor.instrument_app(app)` for automatic tracing
- Add timing and metrics recording to `/slack/events` and `/slack/interactive` endpoints
- Call `tracing_provider.sync_trace_context()` at request start
- Record errors via `metrics_recorder.record_error()`

### 3. `src/emojismith/infrastructure/gcp/worker_app.py`

**Changes:**
- Import and initialize telemetry (same as webhook)
- Add `FastAPIInstrumentor.instrument_app(app)`
- Wrap job processing in OTel span: `tracer.start_as_current_span("process_emoji_job")`
- Record job metrics: `metrics_recorder.record_job_processed(status, provider, duration)`
- Record errors via `metrics_recorder.record_error()`

### 4. `src/emojismith/infrastructure/openai/openai_api.py`

**Changes:**
- Add timing around `generate_image()` call
- Record `metrics_recorder.record_emoji_generated(provider="openai", model=model, is_fallback=..., duration=...)`

### 5. `src/emojismith/infrastructure/google/gemini_api.py`

**Changes:**
- Add timing around image generation
- Record emoji generation metrics (same pattern as OpenAI)

### 6. `pyproject.toml`

**Changes:**
- Add OpenTelemetry dependencies listed above

---

## Testing Strategy

### Unit Tests (TDD - write first)
```
tests/unit/infrastructure/telemetry/
├── test_config.py         # TelemetryConfig defaults, env parsing
├── test_tracing.py        # TracingProvider init, context sync
└── test_metrics.py        # MetricsRecorder safe no-ops when disabled
```

### Integration Tests
```
tests/integration/telemetry/
└── test_trace_propagation.py  # Full trace_id flow through system
```

### Existing Test Updates
- Update `tests/unit/infrastructure/test_logging.py` for new Cloud Logging fields
- Update webhook/worker app tests to mock telemetry components

---

## Environment Configuration

### Production (Cloud Run)
```yaml
GOOGLE_CLOUD_PROJECT: "auto-set"    # Cloud Run provides this
ENVIRONMENT: "production"
TRACE_SAMPLE_RATE: "0.1"            # 10% sampling for cost control
METRICS_ENABLED: "true"
TRACING_ENABLED: "true"
```

### Local Development
```bash
# .env - disables GCP export
GOOGLE_CLOUD_PROJECT=""
METRICS_ENABLED="false"
TRACING_ENABLED="false"
```

---

## Implementation Order

### Phase 1: Foundation (TDD)
1. Add dependencies to `pyproject.toml`
2. Write tests for `TelemetryConfig`
3. Implement `config.py`
4. Write tests for `TracingProvider`
5. Implement `tracing.py`
6. Write tests for `MetricsRecorder`
7. Implement `metrics.py`
8. Create `__init__.py` with exports

### Phase 2: Logging Enhancement
9. Write tests for Cloud Logging fields in `JSONFormatter`
10. Update `logging.py` with trace correlation
11. Update existing logging tests

### Phase 3: App Integration
12. Update `webhook_app.py` with telemetry
13. Update `worker_app.py` with telemetry
14. Update/add tests for app changes

### Phase 4: Deep Instrumentation
15. Add metrics to OpenAI repository
16. Add metrics to Gemini repository
17. Verify all tests pass: `./scripts/check-quality.sh`

### Phase 5: Verification
18. Deploy to staging
19. Verify traces in Cloud Trace console
20. Verify metrics in Cloud Monitoring console
21. Create monitoring dashboard (optional)

---

## Verification Checklist

After implementation, verify:
- [ ] `pytest tests/` passes
- [ ] `ruff check src/ tests/` passes
- [ ] `mypy src/` passes
- [ ] Traces appear in Cloud Trace (staging)
- [ ] Metrics appear in Cloud Monitoring (staging)
- [ ] Logs show `logging.googleapis.com/trace` field
- [ ] Clicking trace link in logs navigates to Cloud Trace

---

## Critical Files Summary

| File | Action |
|------|--------|
| `pyproject.toml` | Add OTel dependencies |
| `src/shared/infrastructure/telemetry/__init__.py` | Create (exports) |
| `src/shared/infrastructure/telemetry/config.py` | Create |
| `src/shared/infrastructure/telemetry/tracing.py` | Create |
| `src/shared/infrastructure/telemetry/metrics.py` | Create |
| `src/shared/infrastructure/logging.py` | Modify (add Cloud Logging fields) |
| `src/emojismith/infrastructure/gcp/webhook_app.py` | Modify (add telemetry) |
| `src/emojismith/infrastructure/gcp/worker_app.py` | Modify (add telemetry) |
| `src/emojismith/infrastructure/openai/openai_api.py` | Modify (add metrics) |
| `src/emojismith/infrastructure/google/gemini_api.py` | Modify (add metrics) |
