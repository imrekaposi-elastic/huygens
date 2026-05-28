"""Process-wide optional audit Kafka producer (configured at service startup)."""

from __future__ import annotations

from huy_events.producer import HuyKafkaProducer

_audit_producer: HuyKafkaProducer | None = None


def configure_audit_publisher(producer: HuyKafkaProducer | None) -> None:
    global _audit_producer
    _audit_producer = producer


def get_audit_publisher() -> HuyKafkaProducer | None:
    return _audit_producer
