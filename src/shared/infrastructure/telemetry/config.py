"""Telemetry configuration utilities."""

from __future__ import annotations

import os
from dataclasses import dataclass


def _parse_bool_env(var_name: str, value: str | None, *, default: bool) -> bool:
    if value is None or value == "":
        return default

    normalized = value.strip().lower()
    if normalized in {"true", "1", "yes", "y", "on"}:
        return True
    if normalized in {"false", "0", "no", "n", "off"}:
        return False

    raise ValueError(f"{var_name} must be a boolean-like value (got: {value!r})")


def _parse_float_env(var_name: str, value: str | None, *, default: float) -> float:
    if value is None or value == "":
        return default
    try:
        parsed = float(value)
    except ValueError as exc:  # pragma: no cover
        raise ValueError(f"{var_name} must be a float (got: {value!r})") from exc
    return parsed


@dataclass(frozen=True)
class TelemetryConfig:
    """Configuration for OpenTelemetry exporters + instrumentation."""

    project_id: str
    service_name: str
    environment: str
    trace_sample_rate: float
    metrics_enabled: bool
    tracing_enabled: bool

    @classmethod
    def from_environment(cls) -> TelemetryConfig:
        project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "")
        service_name = os.environ.get("K_SERVICE") or "emoji-smith"
        environment = os.environ.get("ENVIRONMENT", "development")

        trace_sample_rate = _parse_float_env(
            "TRACE_SAMPLE_RATE",
            os.environ.get("TRACE_SAMPLE_RATE"),
            default=0.1,
        )
        if not (0.0 <= trace_sample_rate <= 1.0):
            raise ValueError("TRACE_SAMPLE_RATE must be between 0.0 and 1.0")

        metrics_enabled = _parse_bool_env(
            "METRICS_ENABLED",
            os.environ.get("METRICS_ENABLED"),
            default=False,
        )
        tracing_enabled = _parse_bool_env(
            "TRACING_ENABLED",
            os.environ.get("TRACING_ENABLED"),
            default=False,
        )

        return cls(
            project_id=project_id,
            service_name=service_name,
            environment=environment,
            trace_sample_rate=trace_sample_rate,
            metrics_enabled=metrics_enabled,
            tracing_enabled=tracing_enabled,
        )
