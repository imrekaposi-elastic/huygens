"""ECS structlog configuration."""

from __future__ import annotations

import json

import structlog
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider

from huy_telemetry.logging_ecs import configure_structlog_ecs


def test_structlog_json_includes_service_and_trace(capsys) -> None:
    configure_structlog_ecs(service_name="huy-registry", log_format="json")
    provider = TracerProvider()
    trace.set_tracer_provider(provider)
    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span("log-test"):
        structlog.get_logger().info("registry_started", version="0.1.0")
    captured = capsys.readouterr().out.strip().splitlines()[-1]
    payload = json.loads(captured)
    assert payload["service.name"] == "huy-registry"
    assert payload["event"] == "registry_started"
    assert "trace.id" in payload
    assert len(payload["trace.id"]) == 32
