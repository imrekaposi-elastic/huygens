"""In-process SSE fan-out hub (fed by Kafka broadcast consumer)."""

from __future__ import annotations

import asyncio
import json
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class InventoryEventHub:
    """Per-process subscriber queues for inventory CloudEvents."""

    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue[str]] = set()
        self._lock = asyncio.Lock()

    async def subscribe(self) -> asyncio.Queue[str]:
        queue: asyncio.Queue[str] = asyncio.Queue(maxsize=64)
        async with self._lock:
            self._subscribers.add(queue)
        return queue

    async def unsubscribe(self, queue: asyncio.Queue[str]) -> None:
        async with self._lock:
            self._subscribers.discard(queue)

    async def publish(self, envelope: dict[str, Any]) -> None:
        line = json.dumps(envelope, separators=(",", ":"))
        async with self._lock:
            targets = list(self._subscribers)
        for queue in targets:
            try:
                queue.put_nowait(line)
            except asyncio.QueueFull:
                logger.warning("sse_subscriber_queue_full", dropping=True)
            except Exception as exc:
                logger.warning("sse_publish_failed", error=str(exc))


_hub: InventoryEventHub | None = None


def get_event_hub() -> InventoryEventHub:
    global _hub
    if _hub is None:
        _hub = InventoryEventHub()
    return _hub


def reset_event_hub_for_tests() -> None:
    """Test isolation."""
    global _hub
    _hub = InventoryEventHub()
