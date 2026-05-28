"""OpenTelemetry spans for Kafka producers and consumers (service map edges)."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from opentelemetry import trace
from opentelemetry.trace import SpanKind, Status, StatusCode

_TRACER_NAME = "huy_events.kafka"
_PEER_KAFKA = "kafka"


def _peer_service_kafka() -> str:
    return _PEER_KAFKA


def _kafka_broker_address(bootstrap: str | None) -> str | None:
    if not bootstrap:
        return None
    first = bootstrap.split(",")[0].strip()
    return first or None


@contextmanager
def kafka_producer_span(
    topic: str,
    *,
    bootstrap: str | None = None,
) -> Iterator[trace.Span]:
    """CLIENT/PRODUCER span for aiokafka publish (links app → kafka in service map)."""
    tracer = trace.get_tracer(_TRACER_NAME)
    attributes: dict[str, Any] = {
        "messaging.system": "kafka",
        "messaging.destination.name": topic,
        "messaging.operation": "publish",
        "peer.service": _peer_service_kafka(),
    }
    broker = _kafka_broker_address(bootstrap)
    if broker:
        attributes["server.address"] = broker
    with tracer.start_as_current_span(
        f"kafka publish {topic}",
        kind=SpanKind.PRODUCER,
        attributes=attributes,
    ) as span:
        try:
            yield span
        except Exception as exc:
            span.set_status(Status(StatusCode.ERROR, str(exc)))
            span.record_exception(exc)
            raise


@contextmanager
def kafka_consumer_span(
    topic: str,
    *,
    bootstrap: str | None = None,
) -> Iterator[trace.Span]:
    """CONSUMER span for aiokafka message handling."""
    tracer = trace.get_tracer(_TRACER_NAME)
    attributes: dict[str, Any] = {
        "messaging.system": "kafka",
        "messaging.destination.name": topic,
        "messaging.operation": "receive",
        "peer.service": _peer_service_kafka(),
    }
    broker = _kafka_broker_address(bootstrap)
    if broker:
        attributes["server.address"] = broker
    with tracer.start_as_current_span(
        f"kafka receive {topic}",
        kind=SpanKind.CONSUMER,
        attributes=attributes,
    ) as span:
        try:
            yield span
        except Exception as exc:
            span.set_status(Status(StatusCode.ERROR, str(exc)))
            span.record_exception(exc)
            raise
