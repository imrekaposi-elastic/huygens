"""OpenTelemetry tracer and meter setup."""

from __future__ import annotations

from typing import Any

from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter as GrpcMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter as GrpcSpanExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter as HttpMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter as HttpSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from huy_telemetry.env import (
    otel_exporter_endpoint,
    otel_exporter_protocol,
    otel_sdk_disabled,
    parse_resource_attributes,
)

_configured = False
_httpx_instrumented = False


def _build_resource(service_name: str, extra_resource: dict[str, str] | None) -> Resource:
    attrs: dict[str, Any] = {"service.name": service_name}
    attrs.update(parse_resource_attributes())
    if extra_resource:
        attrs.update(extra_resource)
    return Resource.create(attrs)


def configure_otel(
    service_name: str,
    *,
    extra_resource: dict[str, str] | None = None,
) -> bool:
    """Install tracer (and optional OTLP export). Returns True when OTLP exporters are active."""
    global _configured
    if _configured or otel_sdk_disabled():
        return False

    resource = _build_resource(service_name, extra_resource)
    tracer_provider = TracerProvider(resource=resource)
    endpoint = otel_exporter_endpoint()
    export_enabled = bool(endpoint)

    if export_enabled:
        protocol = otel_exporter_protocol()
        if protocol == "http":
            span_exporter = HttpSpanExporter(endpoint=endpoint)
            metric_exporter = HttpMetricExporter(endpoint=endpoint)
        else:
            span_exporter = GrpcSpanExporter(endpoint=endpoint)
            metric_exporter = GrpcMetricExporter(endpoint=endpoint)
        tracer_provider.add_span_processor(BatchSpanProcessor(span_exporter))
        metric_reader = PeriodicExportingMetricReader(metric_exporter)
        metrics.set_meter_provider(MeterProvider(resource=resource, metric_readers=[metric_reader]))

    trace.set_tracer_provider(tracer_provider)
    _configured = True
    return export_enabled


def instrument_httpx() -> None:
    global _httpx_instrumented
    if _httpx_instrumented or otel_sdk_disabled():
        return
    HTTPXClientInstrumentor().instrument()
    _httpx_instrumented = True


def instrument_fastapi(
    app: Any,
    *,
    excluded_urls: str = "/readyz,/metrics",
) -> None:
    """Instrument HTTP routes. `/health` is traced (for smoke tests); readiness/metrics are not."""
    if otel_sdk_disabled():
        return
    FastAPIInstrumentor.instrument_app(app, excluded_urls=excluded_urls)


def get_tracer(name: str) -> trace.Tracer:
    return trace.get_tracer(name)


def get_meter(name: str) -> metrics.Meter:
    return metrics.get_meter(name)
