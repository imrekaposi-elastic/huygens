"""Background loop reconciling pending network links."""

from __future__ import annotations

import asyncio

import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from huy_events import HuyKafkaProducer

from huy_projects.config import Settings
from huy_projects.services.agent_proxy import AgentProxy
from huy_projects.services.breakout_client import BreakoutControllerClient
from huy_projects.services.link_reconciler import list_links_to_reconcile, reconcile_link
from huy_projects.services.registry_client import RegistryClient

logger = structlog.get_logger(__name__)


class LinkReconcilerLoop:
    def __init__(
        self,
        settings: Settings,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        kafka_producer: HuyKafkaProducer | None = None,
    ) -> None:
        self._settings = settings
        self._session_factory = session_factory
        self._kafka = kafka_producer
        self._registry = RegistryClient(settings)
        self._proxy = AgentProxy(self._registry)
        self._breakout = BreakoutControllerClient(settings)
        self._task: asyncio.Task | None = None
        self._stop = asyncio.Event()

    async def start(self) -> None:
        self._stop.clear()
        self._task = asyncio.create_task(self._run(), name="link-reconciler")

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
        interval = self._settings.link_reconcile_interval_seconds
        while not self._stop.is_set():
            try:
                await self._tick()
            except Exception:
                logger.exception("link_reconciler_tick_failed")
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=interval)
            except TimeoutError:
                continue

    async def _tick(self) -> None:
        async with self._session_factory() as session:
            links = await list_links_to_reconcile(session)
            for link in links:
                await reconcile_link(
                    session,
                    link,
                    proxy=self._proxy,
                    breakout=self._breakout,
                    settings=self._settings,
                    kafka=self._kafka,
                )
