"""Background inventory polling loop."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from huy_inventory.config import Settings
from huy_inventory.services.agent_poller import poll_agent
from huy_inventory.services.registry_client import RegistryClient
from huy_inventory.services.snapshot_service import upsert_snapshot

logger = structlog.get_logger(__name__)


class InventoryPoller:
    def __init__(
        self,
        settings: Settings,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._settings = settings
        self._session_factory = session_factory
        self._registry = RegistryClient(settings)
        self._task: asyncio.Task | None = None
        self._stop = asyncio.Event()

    async def start(self) -> None:
        self._stop.clear()
        self._task = asyncio.create_task(self._run(), name="inventory-poller")

    async def stop(self) -> None:
        self._stop.set()
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def _run(self) -> None:
        while not self._stop.is_set():
            try:
                await self.poll_once()
            except Exception as exc:
                logger.exception("inventory_poll_cycle_failed", error=str(exc))
            try:
                await asyncio.wait_for(
                    self._stop.wait(),
                    timeout=self._settings.poll_interval_seconds,
                )
            except TimeoutError:
                continue

    async def poll_once(self) -> None:
        targets = await self._registry.fetch_poll_targets()
        for target in targets:
            payload, error = await poll_agent(target)
            polled_at = datetime.now(UTC)
            status = "connected" if error is None else "error"
            async with self._session_factory() as session:
                await upsert_snapshot(
                    session,
                    agent_id=target["agent_id"],
                    organization_id=target["organization_id"],
                    region_id=target["region_id"],
                    payload=payload,
                    poll_error=error,
                )
            try:
                await self._registry.report_poll_status(
                    target["agent_id"],
                    connection_status=status,
                    last_seen_at=polled_at if error is None else None,
                    last_poll_error=error,
                )
            except Exception as exc:
                logger.warning(
                    "registry_poll_status_failed",
                    agent_id=target["agent_id"],
                    error=str(exc),
                )
