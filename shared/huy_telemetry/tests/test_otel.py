"""OTel setup guards."""

from __future__ import annotations

import os

from huy_telemetry.otel import configure_otel


def test_configure_otel_local_traces_without_endpoint(monkeypatch) -> None:
    from opentelemetry import trace

    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    monkeypatch.setenv("OTEL_SDK_DISABLED", "false")
    assert configure_otel("huy-test") is False
    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span("local"):
        assert trace.get_current_span().get_span_context().is_valid


def test_configure_otel_disabled(monkeypatch) -> None:
    monkeypatch.setenv("OTEL_SDK_DISABLED", "true")
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
    assert configure_otel("huy-test") is False
