"""Shared Kafka producer startup for control-plane audit publishing."""

from __future__ import annotations

from huy_events.audit_registry import configure_audit_publisher
from huy_events.config import KafkaSettings
from huy_events.producer import HuyKafkaProducer


async def start_audit_kafka_producer(
    *,
    bootstrap: str,
    service_name: str,
    enabled: bool = True,
    client_id: str | None = None,
) -> HuyKafkaProducer | None:
    if not enabled:
        configure_audit_publisher(None)
        return None
    settings = KafkaSettings(KAFKA_BOOTSTRAP=bootstrap, KAFKA_CLIENT_ID=client_id)
    producer = HuyKafkaProducer(settings, service_name=service_name)
    await producer.start()
    configure_audit_publisher(producer)
    return producer


async def stop_audit_kafka_producer(producer: HuyKafkaProducer | None) -> None:
    configure_audit_publisher(None)
    if producer is not None:
        await producer.stop()
