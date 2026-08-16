"""Unit tests for MetricsRecorder."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest
from opentelemetry.resourcedetector.gcp_resource_detector._mapping import (
    get_monitored_resource,
)

from shared.infrastructure.telemetry.config import TelemetryConfig
from shared.infrastructure.telemetry.metrics import (
    MetricsRecorder,
    _build_metrics_resource,
)


def test_metrics_recorder_noops_when_disabled() -> None:
    config = TelemetryConfig(
        project_id="",
        service_name="emoji-smith",
        environment="development",
        trace_sample_rate=0.0,
        metrics_enabled=False,
        tracing_enabled=False,
    )
    recorder = MetricsRecorder(config=config)

    recorder.record_request(
        endpoint="/health", method="GET", status_code=200, duration_s=0.01
    )
    recorder.record_job_processed(status="ok", provider="openai", duration_s=1.0)
    recorder.record_emoji_generated(
        provider="openai", model="gpt-image-2", is_fallback=False, duration_s=2.0
    )
    recorder.record_error(where="worker", error_type="ValueError")


def test_metrics_recorder_has_instruments_when_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
    config = TelemetryConfig(
        project_id="",
        service_name="emoji-smith",
        environment="test",
        trace_sample_rate=1.0,
        metrics_enabled=True,
        tracing_enabled=False,
    )
    recorder = MetricsRecorder(config=config)

    assert recorder.enabled is True
    assert recorder.http_requests_total is not None
    assert recorder.http_request_duration_seconds is not None


def test_metrics_resource_is_unique_per_process() -> None:
    config = TelemetryConfig(
        project_id="test-project",
        service_name="emoji-smith-webhook",
        environment="test",
        trace_sample_rate=1.0,
        metrics_enabled=True,
        tracing_enabled=False,
    )
    with patch(
        "shared.infrastructure.telemetry.metrics.uuid4",
        return_value=SimpleNamespace(hex="instance-a"),
    ):
        resource = _build_metrics_resource(config)

    monitored_resource = get_monitored_resource(resource)
    assert monitored_resource is not None
    assert monitored_resource.type == "generic_task"
    assert monitored_resource.labels["job"] == "emoji-smith-webhook"
    assert monitored_resource.labels["task_id"] == "instance-a"
