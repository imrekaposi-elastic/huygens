"""Resolve SSH targets for ssh-gateway."""

from __future__ import annotations

from urllib.parse import urlparse

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from huy_inventory.config import Settings
from huy_inventory.services.projects_client import ProjectsClient, assignments_by_resource
from huy_inventory.services.registry_client import RegistryClient
from huy_inventory.services.snapshot_service import get_snapshot, snapshot_to_summary


def _relay_host_from_agent_url(base_url: str) -> str:
    parsed = urlparse(base_url)
    if parsed.hostname:
        return parsed.hostname
    return "127.0.0.1"


def _relay_ws_url_from_agent_url(base_url: str) -> str:
    parsed = urlparse(base_url)
    if not parsed.scheme or not parsed.netloc:
        return ""
    scheme = "wss" if parsed.scheme == "https" else "ws"
    return f"{scheme}://{parsed.netloc}/api/v1/ssh/relay/ws"


async def resolve_ssh_target(
    session: AsyncSession,
    settings: Settings,
    *,
    organization_id: str,
    project_id: str,
    vm_name: str,
) -> dict:
    assignment_rows = await ProjectsClient(settings).fetch_resource_assignments(organization_id)
    assignments = assignments_by_resource(assignment_rows)
    assignment = None
    agent_id = None
    for key, row in assignments.items():
        _aid, rtype, name = key
        if rtype == "vm" and name == vm_name:
            assignment = row
            agent_id = _aid
            break
    if assignment is None or assignment.get("project_id") != project_id:
        raise HTTPException(status_code=404, detail="VM not assigned to project")

    if not agent_id:
        raise HTTPException(status_code=404, detail="VM agent unknown")

    row = await get_snapshot(session, agent_id)
    if row is None or row.organization_id != organization_id:
        raise HTTPException(status_code=404, detail="No inventory for agent")

    summary = snapshot_to_summary(row)
    vm = next((v for v in summary.vms if v.name == vm_name), None)
    if vm is None:
        raise HTTPException(status_code=404, detail="VM not in inventory")

    guest_ip = vm.ips[0] if vm.ips else None
    if not guest_ip:
        raise HTTPException(status_code=404, detail="VM guest IP unknown")

    targets = await RegistryClient(settings).fetch_poll_targets()
    agent_meta = next((t for t in targets if t["agent_id"] == agent_id), None)
    if agent_meta is None:
        raise HTTPException(status_code=404, detail="Agent not registered")

    relay_host = _relay_host_from_agent_url(agent_meta.get("base_url", ""))
    relay_ws_url = _relay_ws_url_from_agent_url(agent_meta.get("base_url", ""))
    ssh_ready = vm.guest_status in ("running", "ready", None) and bool(guest_ip)

    return {
        "organization_id": organization_id,
        "project_id": project_id,
        "agent_id": agent_id,
        "vm_name": vm_name,
        "guest_ip": guest_ip,
        "relay_host": relay_host,
        "relay_port": 9122,
        "relay_ws_url": relay_ws_url,
        "ssh_ready": ssh_ready,
        "ips": vm.ips,
    }
