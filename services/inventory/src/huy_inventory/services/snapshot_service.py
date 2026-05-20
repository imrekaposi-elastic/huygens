"""Persist and query inventory snapshots."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from huy_inventory.libvirt_system import is_system_network, managed_networks
from huy_inventory.models import InventorySnapshot
from huy_inventory.schemas import (
    AgentInventorySummary,
    NetworkInventoryItem,
    OrganizationDashboard,
    SnapshotOut,
    VmInventoryItem,
)


def _drift_detected(previous: dict | None, current: dict) -> bool:
    if previous is None:
        return False
    def _net_key(payload: dict) -> list:
        return sorted(
            (n.get("name"), n.get("active"))
            for n in managed_networks(payload.get("networks", []))
        )

    prev_key = {
        "vms": sorted((v.get("name"), v.get("state")) for v in previous.get("vms", [])),
        "networks": _net_key(previous),
    }
    cur_key = {
        "vms": sorted((v.get("name"), v.get("state")) for v in current.get("vms", [])),
        "networks": _net_key(current),
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
        # After a failed poll or re-enrollment, first successful poll is a baseline — not drift.
        if existing is not None and existing.poll_error:
            config_drift = False
        else:
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


async def delete_snapshot(session: AsyncSession, agent_id: str) -> bool:
    row = await get_snapshot(session, agent_id)
    if row is None:
        return False
    await session.delete(row)
    await session.commit()
    return True


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


def _apply_project_assignment(
    item: VmInventoryItem | NetworkInventoryItem,
    *,
    agent_id: str,
    resource_type: str,
    assignments: dict[tuple[str, str, str], dict],
) -> None:
    name = item.name or ""
    assignment = assignments.get((agent_id, resource_type, name))
    if assignment is None:
        item.orphaned = True
        return
    item.orphaned = False
    item.project_id = assignment.get("project_id")
    item.project_name = assignment.get("project_name")
    item.project_slug = assignment.get("project_slug")


def snapshot_to_summary(
    row: InventorySnapshot,
    *,
    agent_name: str | None = None,
    connection_status: str | None = None,
    assignments: dict[tuple[str, str, str], dict] | None = None,
) -> AgentInventorySummary:
    assignments = assignments or {}
    vms_raw = row.payload.get("vms", [])
    nets_raw = managed_networks(row.payload.get("networks", []))
    vms = [
        VmInventoryItem(
            name=v.get("name"),
            state=v.get("state"),
            libvirt_state=v.get("libvirt_state"),
            guest_status=v.get("guest_status"),
            memory_mib=v.get("memory_mib"),
            ips=v.get("ips") or [],
            networks=v.get("networks") or [],
        )
        for v in vms_raw
    ]
    networks = [
        NetworkInventoryItem(
            name=n.get("name"),
            active=n.get("active"),
            readonly=n.get("readonly"),
            bridge=n.get("bridge"),
            system=is_system_network(n.get("name")),
        )
        for n in nets_raw
    ]
    for vm in vms:
        _apply_project_assignment(vm, agent_id=row.agent_id, resource_type="vm", assignments=assignments)
    for net in networks:
        _apply_project_assignment(
            net, agent_id=row.agent_id, resource_type="network", assignments=assignments
        )
    orphaned_vm_count = sum(1 for v in vms if v.orphaned)
    orphaned_network_count = sum(1 for n in networks if n.orphaned)
    return AgentInventorySummary(
        agent_id=row.agent_id,
        agent_name=agent_name,
        organization_id=row.organization_id,
        region_id=row.region_id,
        polled_at=row.polled_at,
        config_drift=row.config_drift,
        poll_error=row.poll_error,
        vm_count=len(vms),
        network_count=len(networks),
        connection_status=connection_status,
        vms=vms,
        networks=networks,
        orphaned_vm_count=orphaned_vm_count,
        orphaned_network_count=orphaned_network_count,
    )


async def organization_dashboard(
    session: AsyncSession,
    organization_id: str,
    *,
    active_agent_ids: set[str] | None = None,
    registry_by_id: dict[str, dict] | None = None,
    assignments: dict[tuple[str, str, str], dict] | None = None,
) -> OrganizationDashboard:
    rows = await list_snapshots(session, organization_id=organization_id)
    if active_agent_ids is not None:
        rows = [r for r in rows if r.agent_id in active_agent_ids]
    registry_by_id = registry_by_id or {}
    assignments = assignments or {}
    agents = [
        snapshot_to_summary(
            r,
            agent_name=registry_by_id.get(r.agent_id, {}).get("name"),
            connection_status=registry_by_id.get(r.agent_id, {}).get("connection_status"),
            assignments=assignments,
        )
        for r in rows
    ]
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
