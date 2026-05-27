"""Log compliance checks nearing expiry (FRAMEWORK_PLAN alerter MVP)."""

from __future__ import annotations

import asyncio
from datetime import timedelta

import structlog
from sqlalchemy import select

from huy_compliance.config import Settings
from huy_compliance.db import get_session_factory
from huy_compliance.models import ComplianceCheck, utc_now

logger = structlog.get_logger(__name__)


class CheckAlerterLoop:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._task: asyncio.Task[None] | None = None
        self._stop = asyncio.Event()

    async def start(self) -> None:
        self._stop.clear()
        self._task = asyncio.create_task(self._run(), name="compliance-check-alerter")

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
        interval = max(60, self._settings.check_alert_interval_seconds)
        while not self._stop.is_set():
            try:
                await self._scan()
            except Exception:
                logger.exception("compliance_check_alerter_failed")
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=interval)
            except TimeoutError:
                continue

    async def _scan(self) -> None:
        factory = get_session_factory()
        soon = utc_now() + timedelta(days=30)
        async with factory() as session:
            rows = (
                await session.scalars(
                    select(ComplianceCheck).where(
                        ComplianceCheck.status == "active",
                        ComplianceCheck.valid_until <= soon,
                    )
                )
            ).all()
            for row in rows:
                logger.warning(
                    "compliance_check_expiring",
                    organization_id=row.organization_id,
                    check_id=row.id,
                    compliance_item_id=row.compliance_item_id,
                    valid_until=row.valid_until.isoformat(),
                    owner_user_id=row.owner_user_id,
                )
