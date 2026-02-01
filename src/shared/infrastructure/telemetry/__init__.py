"""OpenTelemetry-based observability helpers.

This package lives in shared infrastructure so it can be used by both Cloud Run
services (webhook + worker) without leaking observability concerns into the
domain layer.
"""

from shared.infrastructure.telemetry.config import TelemetryConfig
from shared.infrastructure.telemetry.metrics import (
    MetricsRecorder,
    create_metrics_recorder,
)
from shared.infrastructure.telemetry.tracing import (
    TracingProvider,
    create_tracing_provider,
)

__all__ = [
    "MetricsRecorder",
    "TelemetryConfig",
    "TracingProvider",
    "create_metrics_recorder",
    "create_tracing_provider",
]
