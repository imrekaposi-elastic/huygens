"""Publish network link events to Kafka."""

from __future__ import annotations

from typing import Any

import structlog
from huy_events import HuyKafkaProducer, build_envelope

logger = structlog.get_logger(__name__)

TOPIC_NETWORK_LINKS = "huy.network.links"
LINK_EVENT_TYPE = "com.huygens.network.link.v1"
LINK_EVENT_SOURCE = "/services/projects/link-reconciler"
LINK_EVENT_DATASCHEMA = "https://huygens.dev/schemas/kafka/com.huygens.network.link.v1.json"


def link_event_data(link: Any) -> dict[str, Any]:
    return {
        "version": 1,
        "link_id": link.id,
        "organization_id": link.organization_id,
        "status": link.status,
        "left_agent_id": link.left_agent_id,
        "right_agent_id": link.right_agent_id,
    }


async def publish_link_event(producer: HuyKafkaProducer, link: Any) -> None:
    data = link_event_data(link)
    envelope = build_envelope(
        event_type=LINK_EVENT_TYPE,
        source=LINK_EVENT_SOURCE,
        data=data,
        subject=data["link_id"],
        dataschema=LINK_EVENT_DATASCHEMA,
    )
    await producer.send(TOPIC_NETWORK_LINKS, envelope, key=data["link_id"])
    logger.debug("network_link_event_published", link_id=data["link_id"], status=data["status"])
