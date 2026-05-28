"""OpenTelemetry setup for the libvirt agent (traces + OTLP metrics via huy_telemetry)."""

from __future__ import annotations

import os

from huy_telemetry import prepare_service_telemetry

from huy_libvirt_agent.config import Settings


def _apply_otel_env(settings: Settings) -> None:
    if settings.otel_exporter_otlp_endpoint:
        os.environ.setdefault("OTEL_EXPORTER_OTLP_ENDPOINT", settings.otel_exporter_otlp_endpoint)


def agent_resource_attributes(settings: Settings) -> dict[str, str]:
    return {
        "huy.agent.country": settings.agent_country,
        "huy.agent.city": settings.agent_city,
        "huy.agent.company": settings.agent_company,
    }


def setup_telemetry(settings: Settings) -> bool:
    """Configure structlog ECS fields, tracing, and OTLP export. Returns True when OTLP is active."""
    _apply_otel_env(settings)
    return prepare_service_telemetry(
        settings.otel_service_name,
        extra_resource=agent_resource_attributes(settings),
    )
