"""Unit tests for TelemetryConfig."""

from __future__ import annotations

import pytest

from shared.infrastructure.telemetry.config import TelemetryConfig


def test_from_environment_parses_values(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "test-project")
    monkeypatch.setenv("K_SERVICE", "emoji-smith-webhook")
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("TRACE_SAMPLE_RATE", "0.25")
    monkeypatch.setenv("METRICS_ENABLED", "true")
    monkeypatch.setenv("TRACING_ENABLED", "false")

    config = TelemetryConfig.from_environment()

    assert config.project_id == "test-project"
    assert config.service_name == "emoji-smith-webhook"
    assert config.environment == "production"
    assert config.trace_sample_rate == 0.25
    assert config.metrics_enabled is True
    assert config.tracing_enabled is False


def test_from_environment_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
    monkeypatch.delenv("K_SERVICE", raising=False)
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.delenv("TRACE_SAMPLE_RATE", raising=False)
    monkeypatch.delenv("METRICS_ENABLED", raising=False)
    monkeypatch.delenv("TRACING_ENABLED", raising=False)

    config = TelemetryConfig.from_environment()

    assert config.project_id == ""
    assert config.environment == "development"
    assert config.metrics_enabled is False
    assert config.tracing_enabled is False


def test_from_environment_rejects_invalid_sampling_rate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TRACE_SAMPLE_RATE", "not-a-float")
    with pytest.raises(ValueError, match="TRACE_SAMPLE_RATE"):
        TelemetryConfig.from_environment()


@pytest.mark.parametrize("value", ["wat", "2", "TRUE-ish"])
def test_from_environment_rejects_invalid_bool(
    monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    monkeypatch.setenv("METRICS_ENABLED", value)
    with pytest.raises(ValueError, match="METRICS_ENABLED"):
        TelemetryConfig.from_environment()
