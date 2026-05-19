"""Persist and query inventory snapshots."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from huy_inventory.models import InventorySnapshot
from huy_inventory.schemas import AgentInventorySummary, OrganizationDashboard, SnapshotOut


def _drift_detected(previous: dict | None, current: dict) -> bool:
    if previous is None:
        return False
    prev_key = {
        "vms": sorted((v.get("name"), v.get("state")) for v in previous.get("vms", [])),
        "networks": sorted((n.get("name"), n.get("active")) for n in previous.get("networks", [])),
    }
    cur_key = {
        "vms": sorted((v.get("name"), v.get("state")) for v in current.get("vms", [])),
        "networks": sorted((n.get("name"), n.get("active")) for n in current.get("networks", [])),
    }
    return prev_key != cur_key


async def upsert_snapshot(
    session: AsyncSession,
    *,
    agent_id: str,
    organization_id: str,
    region_id: str,
    payload: dict[str, Any] | None,
    poll_error: str | None,
) -> InventorySnapshot:
    result = await session.execute(
        select(InventorySnapshot).where(InventorySnapshot.agent_id == agent_id)
    )
    existing = result.scalar_one_or_none()
    polled_at = datetime.now(UTC)
    if payload is not None:
        config_drift = _drift_detected(existing.payload if existing else None, payload)
        payload["config_drift"] = config_drift
    else:
        config_drift = False
        payload = existing.payload if existing else {
            "version": 1,
            "agent_id": agent_id,
            "organization_id": organization_id,
            "region_id": region_id,
            "polled_at": polled_at.isoformat(),
            "vms": [],
            "networks": [],
            "config_drift": False,
        }

    if existing is None:
        row = InventorySnapshot(
            agent_id=agent_id,
            organization_id=organization_id,
            region_id=region_id,
            polled_at=polled_at,
            payload=payload,
            config_drift=config_drift,
            poll_error=poll_error,
        )
        session.add(row)
    else:
        existing.polled_at = polled_at
        if poll_error is None:
            existing.payload = payload
            existing.config_drift = config_drift
        existing.poll_error = poll_error
        row = existing
    await session.commit()
    await session.refresh(row)
    return row


async def get_snapshot(session: AsyncSession, agent_id: str) -> InventorySnapshot | None:
    result = await session.execute(
        select(InventorySnapshot).where(InventorySnapshot.agent_id == agent_id)
    )
    return result.scalar_one_or_none()


async def list_snapshots(
    session: AsyncSession, organization_id: str | None = None
) -> list[InventorySnapshot]:
    stmt = select(InventorySnapshot).order_by(InventorySnapshot.agent_id)
    if organization_id is not None:
        stmt = stmt.where(InventorySnapshot.organization_id == organization_id)
    result = await session.execute(stmt)
    return list(result.scalars().all())


def snapshot_to_summary(row: InventorySnapshot) -> AgentInventorySummary:
    vms = row.payload.get("vms", [])
    networks = row.payload.get("networks", [])
    return AgentInventorySummary(
        agent_id=row.agent_id,
        organization_id=row.organization_id,
        region_id=row.region_id,
        polled_at=row.polled_at,
        config_drift=row.config_drift,
        poll_error=row.poll_error,
        vm_count=len(vms),
        network_count=len(networks),
    )


async def organization_dashboard(
    session: AsyncSession, organization_id: str
) -> OrganizationDashboard:
    rows = await list_snapshots(session, organization_id=organization_id)
    agents = [snapshot_to_summary(r) for r in rows]
    vm_count = sum(a.vm_count for a in agents)
    network_count = sum(a.network_count for a in agents)
    return OrganizationDashboard(
        organization_id=organization_id,
        agent_count=len(agents),
        vm_count=vm_count,
        network_count=network_count,
        agents_with_drift=sum(1 for a in agents if a.config_drift),
        agents_with_errors=sum(1 for a in agents if a.poll_error),
        agents=agents,
    )


def snapshot_to_out(row: InventorySnapshot) -> SnapshotOut:
    return SnapshotOut.model_validate(row)
