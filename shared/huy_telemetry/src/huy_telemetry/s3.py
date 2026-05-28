"""S3-compatible object store client spans (SeaweedFS, MinIO, AWS S3)."""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any
from urllib.parse import urlparse

from opentelemetry import trace
from opentelemetry.trace import SpanKind, Status, StatusCode

from huy_telemetry.env import otel_sdk_disabled

_TRACER_NAME = "huy_telemetry.s3"
_DEFAULT_PEER = "seaweedfs"


def _peer_service_name() -> str:
    return os.getenv("OTEL_PEER_OBJECT_STORE_SERVICE_NAME", _DEFAULT_PEER).strip() or _DEFAULT_PEER


def _server_address(endpoint: str | None) -> str | None:
    if not endpoint:
        return None
    parsed = urlparse(endpoint if "://" in endpoint else f"http://{endpoint}")
    return parsed.netloc or parsed.path or None


@contextmanager
def s3_client_span(
    operation: str,
    *,
    bucket: str | None = None,
    key: str | None = None,
    endpoint: str | None = None,
) -> Iterator[trace.Span]:
    """CLIENT span for boto3 S3 calls (service map edge → SeaweedFS by default)."""
    if otel_sdk_disabled():
        yield trace.get_current_span()
        return

    attributes: dict[str, Any] = {
        "rpc.system": "aws-api",
        "rpc.service": "S3",
        "rpc.method": operation,
        "peer.service": _peer_service_name(),
    }
    if bucket:
        attributes["aws.s3.bucket"] = bucket
    if key:
        attributes["aws.s3.key"] = key
    host = _server_address(endpoint)
    if host:
        attributes["server.address"] = host

    tracer = trace.get_tracer(_TRACER_NAME)
    with tracer.start_as_current_span(
        f"S3 {operation}",
        kind=SpanKind.CLIENT,
        attributes=attributes,
    ) as span:
        try:
            yield span
        except Exception as exc:
            span.set_status(Status(StatusCode.ERROR, str(exc)))
            span.record_exception(exc)
            raise
