"""OpenTelemetry tracing and metrics setup."""

from __future__ import annotations

from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from huy_libvirt_agent.config import Settings


def setup_telemetry(settings: Settings) -> None:
    resource = Resource.create(
        {
            "service.name": settings.otel_service_name,
            "huy.agent.country": settings.agent_country,
            "huy.agent.city": settings.agent_city,
            "huy.agent.company": settings.agent_company,
        }
    )
    provider = TracerProvider(resource=resource)
    if settings.otel_exporter_otlp_endpoint:
        provider.add_span_processor(
            BatchSpanProcessor(OTLPSpanExporter(endpoint=settings.otel_exporter_otlp_endpoint))
        )
    trace.set_tracer_provider(provider)
    metrics.set_meter_provider(MeterProvider(resource=resource))


def get_tracer(name: str) -> trace.Tracer:
    return trace.get_tracer(name)
