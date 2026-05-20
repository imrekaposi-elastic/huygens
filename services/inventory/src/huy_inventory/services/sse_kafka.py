"""Kafka broadcast consumer → SSE hub."""

from __future__ import annotations

import asyncio
import socket
from typing import Any

import structlog
from huy_events import HuyBroadcastConsumer, KafkaSettings, TOPIC_INVENTORY_SNAPSHOTS

from huy_auth.auth_context import AuthContext
from huy_inventory.services.sse_hub import InventoryEventHub

logger = structlog.get_logger(__name__)


def broadcast_group_id(prefix: str = "inventory-sse") -> str:
    host = socket.gethostname().replace(".", "-")
    return f"{prefix}-{host}"


def user_may_receive_event(user: AuthContext, envelope: dict[str, Any]) -> bool:
    if user.is_platform_admin():
        return True
    data = envelope.get("data") or {}
    org_id = data.get("organization_id")
    if not org_id:
        return False
    return user.can_access_org(str(org_id))


class InventorySseKafkaBridge:
    def __init__(self, kafka_settings: KafkaSettings, hub: InventoryEventHub) -> None:
        self._hub = hub
        self._consumer = HuyBroadcastConsumer(
            kafka_settings,
            group_id=broadcast_group_id(),
            topics=[TOPIC_INVENTORY_SNAPSHOTS],
            handler=self._on_message,
        )
        self._task: asyncio.Task | None = None

    async def _on_message(self, envelope: dict[str, Any]) -> None:
        await self._hub.publish(envelope)

    async def start(self) -> None:
        await self._consumer.start()
        self._task = asyncio.create_task(self._consumer.run_forever(), name="inventory-sse-kafka")

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        await self._consumer.stop()
