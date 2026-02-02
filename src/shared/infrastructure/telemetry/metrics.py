"""OpenTelemetry metrics setup and recording helpers."""

from __future__ import annotations

import logging
from typing import cast

from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import MetricExporter
from opentelemetry.sdk.resources import Resource

from shared.infrastructure.telemetry.config import TelemetryConfig

logger = logging.getLogger(__name__)


def create_metrics_recorder(config: TelemetryConfig) -> MetricsRecorder:
    return MetricsRecorder(config=config)


class MetricsRecorder:
    """Records key application metrics via OpenTelemetry."""

    def __init__(self, *, config: TelemetryConfig) -> None:
        self._config = config
        self._enabled = config.metrics_enabled

        self.http_requests_total = None
        self.http_request_duration_seconds = None
        self.jobs_total = None
        self.job_duration_seconds = None
        self.emojis_generated_total = None
        self.image_generation_duration_seconds = None
        self.errors_total = None

        if not self._enabled:
            return

        provider = _build_meter_provider(config)
        if provider is not None:
            metrics.set_meter_provider(provider)

        meter = metrics.get_meter(config.service_name)

        self.http_requests_total = meter.create_counter(
            name="http_requests_total",
            unit="1",
            description="Total HTTP requests processed.",
        )
        self.http_request_duration_seconds = meter.create_histogram(
            name="http_request_duration_seconds",
            unit="s",
            description="HTTP request duration in seconds.",
        )
        self.jobs_total = meter.create_counter(
            name="jobs_total",
            unit="1",
            description="Total background jobs processed.",
        )
        self.job_duration_seconds = meter.create_histogram(
            name="job_duration_seconds",
            unit="s",
            description="Job processing duration in seconds.",
        )
        self.emojis_generated_total = meter.create_counter(
            name="emojis_generated_total",
            unit="1",
            description="Total emojis generated.",
        )
        self.image_generation_duration_seconds = meter.create_histogram(
            name="image_generation_duration_seconds",
            unit="s",
            description="Image generation duration in seconds.",
        )
        self.errors_total = meter.create_counter(
            name="errors_total",
            unit="1",
            description="Total errors recorded.",
        )

    @property
    def enabled(self) -> bool:
        return self._enabled

    def record_request(
        self,
        *,
        endpoint: str,
        method: str,
        status_code: int,
        duration_s: float,
    ) -> None:
        if not self._enabled or self.http_requests_total is None:
            return
        attributes: dict[str, str | bool | int | float] = {
            "endpoint": endpoint,
            "method": method,
            "status_code": status_code,
        }
        self.http_requests_total.add(1, attributes)
        if self.http_request_duration_seconds is not None:
            self.http_request_duration_seconds.record(duration_s, attributes)

    def record_job_processed(
        self,
        *,
        status: str,
        provider: str,
        duration_s: float,
    ) -> None:
        if not self._enabled or self.jobs_total is None:
            return
        attributes: dict[str, str | bool | int | float] = {
            "status": status,
            "provider": provider,
        }
        self.jobs_total.add(1, attributes)
        if self.job_duration_seconds is not None:
            self.job_duration_seconds.record(duration_s, attributes)

    def record_emoji_generated(
        self,
        *,
        provider: str,
        model: str,
        is_fallback: bool,
        duration_s: float,
    ) -> None:
        if not self._enabled or self.emojis_generated_total is None:
            return
        attributes: dict[str, str | bool | int | float] = {
            "provider": provider,
            "model": model,
            "is_fallback": is_fallback,
        }
        self.emojis_generated_total.add(1, attributes)
        if self.image_generation_duration_seconds is not None:
            self.image_generation_duration_seconds.record(duration_s, attributes)

    def record_error(self, *, where: str, error_type: str) -> None:
        if not self._enabled or self.errors_total is None:
            return
        attributes: dict[str, str | bool | int | float] = {
            "where": where,
            "error_type": error_type,
        }
        self.errors_total.add(1, attributes)


def _build_meter_provider(config: TelemetryConfig) -> MeterProvider | None:
    base_resource = Resource.create(
        {
            "service.name": config.service_name,
            "deployment.environment": config.environment,
        }
    )

    # Use GCP resource detector to properly identify Cloud Run resources.
    # This prevents "Points must be written in order" errors by giving each
    # Cloud Run instance a unique resource identity.
    resource = _get_gcp_resource(base_resource)

    exporter = _build_cloud_monitoring_exporter(config.project_id)
    if exporter is None:
        # Still provide a meter provider so `metrics.get_meter()` works.
        return MeterProvider(resource=resource)

    try:
        from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
    except Exception:  # pragma: no cover
        return MeterProvider(resource=resource)

    reader = PeriodicExportingMetricReader(exporter)
    return MeterProvider(resource=resource, metric_readers=[reader])


def _get_gcp_resource(base_resource: Resource) -> Resource:
    """Merge base resource with GCP-detected resource attributes."""
    try:
        from opentelemetry.resourcedetector.gcp_resource_detector import (
            GoogleCloudResourceDetector,
        )
        from opentelemetry.sdk.resources import get_aggregated_resources

        return get_aggregated_resources(
            [GoogleCloudResourceDetector(raise_on_error=False)],
            initial_resource=base_resource,
        )
    except Exception:  # pragma: no cover - optional dependency
        logger.debug("GCP resource detector unavailable", exc_info=True)
        return base_resource


def _build_cloud_monitoring_exporter(project_id: str) -> MetricExporter | None:
    if not project_id:
        return None

    try:
        from opentelemetry.exporter.cloud_monitoring import (
            CloudMonitoringMetricsExporter,
        )
    except Exception:  # pragma: no cover - dependency/import variation
        logger.debug("Cloud Monitoring exporter unavailable", exc_info=True)
        return None

    try:
        return cast(
            MetricExporter, CloudMonitoringMetricsExporter(project_id=project_id)
        )
    except TypeError:
        return cast(MetricExporter, CloudMonitoringMetricsExporter())
