"""Background loop pruning network assignments absent from agents."""

from __future__ import annotations

import asyncio

import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from huy_projects.config import Settings
from huy_projects.services.agent_proxy import AgentProxy
from huy_projects.services.assignment_reconciler import reconcile_stale_network_assignments
from huy_projects.services.registry_client import RegistryClient

logger = structlog.get_logger(__name__)


class AssignmentReconcilerLoop:
    def __init__(
        self,
        settings: Settings,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._settings = settings
        self._session_factory = session_factory
        self._registry = RegistryClient(settings)
        self._proxy = AgentProxy(self._registry)
        self._task: asyncio.Task | None = None
        self._stop = asyncio.Event()

    async def start(self) -> None:
        self._stop.clear()
        self._task = asyncio.create_task(self._run(), name="assignment-reconciler")

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
        interval = self._settings.assignment_reconcile_interval_seconds
        while not self._stop.is_set():
            try:
                await self._tick()
            except Exception:
                logger.exception("assignment_reconciler_tick_failed")
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=interval)
            except TimeoutError:
                continue

    async def _tick(self) -> None:
        async with self._session_factory() as session:
            removed = await reconcile_stale_network_assignments(
                session, proxy=self._proxy
            )
            if removed:
                logger.info("assignment_reconcile_tick", removed=removed)
