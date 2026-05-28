"""Kafka span attributes for service map dependencies."""

from __future__ import annotations

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.sdk.trace.export import SimpleSpanProcessor

from huy_events.tracing import kafka_producer_span


def test_kafka_producer_span_attributes() -> None:
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    with kafka_producer_span("huy.audit.events", bootstrap="kafka:9092"):
        pass

    spans = exporter.get_finished_spans()
    assert len(spans) == 1
    attrs = dict(spans[0].attributes or {})
    assert attrs.get("messaging.system") == "kafka"
    assert attrs.get("messaging.destination.name") == "huy.audit.events"
    assert attrs.get("peer.service") == "kafka"
    assert attrs.get("server.address") == "kafka:9092"
