"""Shared OpenTelemetry and ECS logging for Huygens services."""

from huy_telemetry.context import audit_log_fields, current_trace_ids
from huy_telemetry.logging_ecs import configure_structlog_ecs
from huy_telemetry.fastapi_setup import attach_fastapi_telemetry, prepare_service_telemetry
from huy_telemetry.middleware import install_request_context_middleware
from huy_telemetry.db import instrument_sqlalchemy, register_async_sqlalchemy_engine
from huy_telemetry.s3 import s3_client_span
from huy_telemetry.otel import configure_otel, get_meter, get_tracer, instrument_fastapi, instrument_httpx

__all__ = [
    "attach_fastapi_telemetry",
    "audit_log_fields",
    "configure_otel",
    "configure_structlog_ecs",
    "current_trace_ids",
    "get_meter",
    "get_tracer",
    "install_request_context_middleware",
    "instrument_fastapi",
    "instrument_httpx",
    "instrument_sqlalchemy",
    "prepare_service_telemetry",
    "register_async_sqlalchemy_engine",
    "s3_client_span",
]
