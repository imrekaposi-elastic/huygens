"""Read standard OpenTelemetry environment variables."""

from __future__ import annotations

import os


def otel_sdk_disabled() -> bool:
    return os.getenv("OTEL_SDK_DISABLED", "").strip().lower() in ("true", "1", "yes")


def otel_exporter_endpoint() -> str | None:
    value = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip()
    return value or None


def otel_exporter_protocol() -> str:
    """Return grpc or http/protobuf (default grpc)."""
    value = os.getenv("OTEL_EXPORTER_OTLP_PROTOCOL", "grpc").strip().lower()
    if value in ("http/protobuf", "http"):
        return "http"
    return "grpc"


def parse_resource_attributes() -> dict[str, str]:
    raw = os.getenv("OTEL_RESOURCE_ATTRIBUTES", "").strip()
    if not raw:
        return {}
    attrs: dict[str, str] = {}
    for part in raw.split(","):
        piece = part.strip()
        if not piece or "=" not in piece:
            continue
        key, _, val = piece.partition("=")
        attrs[key.strip()] = val.strip()
    return attrs
