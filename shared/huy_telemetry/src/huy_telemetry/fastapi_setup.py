"""Bootstrap helpers for FastAPI control-plane services."""

from __future__ import annotations

from typing import Any

from huy_telemetry.logging_ecs import configure_structlog_ecs
from huy_telemetry.middleware import install_request_context_middleware
from huy_telemetry.otel import configure_otel, instrument_fastapi, instrument_httpx


def prepare_service_telemetry(
    service_name: str,
    *,
    extra_resource: dict[str, str] | None = None,
) -> bool:
    """Configure structlog + tracer; returns True when OTLP export is enabled."""
    configure_structlog_ecs(service_name=service_name)
    export_enabled = configure_otel(service_name, extra_resource=extra_resource)
    instrument_httpx()
    return export_enabled


def attach_fastapi_telemetry(app: Any, *, export_enabled: bool) -> None:
    app.state.otel_export_enabled = export_enabled
    install_request_context_middleware(app)
    instrument_fastapi(app)
