"""Publish inventory snapshots to Kafka (CloudEvents)."""

from __future__ import annotations

from typing import Any

import structlog
from huy_events import (
    HuyKafkaProducer,
    KafkaSettings,
    TOPIC_INVENTORY_SNAPSHOTS,
    build_envelope,
)

logger = structlog.get_logger(__name__)

INVENTORY_SNAPSHOT_TYPE = "com.huygens.inventory.snapshot.v1"
INVENTORY_SNAPSHOT_SOURCE = "/services/inventory/poller"
INVENTORY_SNAPSHOT_DATASCHEMA = (
    "https://huygens.dev/schemas/kafka/inventory-snapshot.schema.json"
)


def kafka_event_data(payload: dict[str, Any]) -> dict[str, Any]:
    """Strip fields not in inventory-snapshot.schema.json (e.g. agent metadata blob)."""
    return {
        "version": payload["version"],
        "agent_id": payload["agent_id"],
        "organization_id": payload["organization_id"],
        "region_id": payload["region_id"],
        "polled_at": payload["polled_at"],
        "vms": payload["vms"],
        "networks": payload["networks"],
        "config_drift": payload.get("config_drift", False),
    }


async def publish_inventory_snapshot(
    producer: HuyKafkaProducer,
    payload: dict[str, Any],
) -> None:
    data = kafka_event_data(payload)
    envelope = build_envelope(
        event_type=INVENTORY_SNAPSHOT_TYPE,
        source=INVENTORY_SNAPSHOT_SOURCE,
        data=data,
        subject=data["agent_id"],
        time=data["polled_at"],
        dataschema=INVENTORY_SNAPSHOT_DATASCHEMA,
    )
    await producer.send(TOPIC_INVENTORY_SNAPSHOTS, envelope, key=data["agent_id"])
    logger.debug("inventory_snapshot_published", agent_id=data["agent_id"])


def create_kafka_producer(settings: KafkaSettings) -> HuyKafkaProducer:
    return HuyKafkaProducer(settings, service_name="inventory")
