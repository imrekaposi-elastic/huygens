"""Config drift detection edge cases."""

from __future__ import annotations

import pytest

from huy_inventory.config import get_settings
from huy_inventory.db import get_engine, get_session_factory, init_db
from huy_inventory.models import Base
from huy_inventory.services.snapshot_service import upsert_snapshot


@pytest.mark.asyncio
async def test_no_drift_after_recovering_from_poll_error() -> None:
    settings = get_settings()
    init_db(settings)
    async with get_engine().begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    org_id = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    agent_id = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
    region_id = "cccccccc-cccc-cccc-cccc-cccccccccccc"

    async with get_session_factory()() as session:
        await upsert_snapshot(
            session,
            agent_id=agent_id,
            organization_id=org_id,
            region_id=region_id,
            payload=None,
            poll_error="connection refused",
        )

        payload = {
            "version": 1,
            "agent_id": agent_id,
            "organization_id": org_id,
            "region_id": region_id,
            "vms": [{"name": "web-01", "state": "RUNNING"}],
            "networks": [{"name": "default", "active": True}],
        }
        row = await upsert_snapshot(
            session,
            agent_id=agent_id,
            organization_id=org_id,
            region_id=region_id,
            payload=payload,
            poll_error=None,
        )
        assert row.config_drift is False
