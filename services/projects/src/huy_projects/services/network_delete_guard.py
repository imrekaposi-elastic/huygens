"""Pre-delete checks for virtual networks."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from huy_projects.models import NetworkLink, Project
from huy_projects.services.agent_proxy import AgentProxy


def _breakout_is_active(breakout: dict[str, Any]) -> bool:
    wg = breakout.get("wireguard") or {}
    flat = breakout.get("flat") or {}
    return bool(wg.get("enabled")) or bool(flat.get("enabled"))


async def _vms_using_network(
    proxy: AgentProxy,
    *,
    agent_id: str,
    organization_id: str,
    network_name: str,
) -> list[str]:
    vms = await proxy.list_vms(agent_id, organization_id)
    return sorted(
        vm["name"]
        for vm in vms
        if vm.get("name") and vm.get("network") == network_name
    )


async def _active_links_for_endpoint(
    session: AsyncSession,
    organization_id: str,
    *,
    agent_id: str,
    project_id: str,
    network_name: str,
) -> list[NetworkLink]:
    result = await session.execute(
        select(NetworkLink).where(
            NetworkLink.organization_id == organization_id,
            NetworkLink.status != "deleting",
            or_(
                (
                    (NetworkLink.left_agent_id == agent_id)
                    & (NetworkLink.left_project_id == project_id)
                    & (NetworkLink.left_network_name == network_name)
                ),
                (
                    (NetworkLink.right_agent_id == agent_id)
                    & (NetworkLink.right_project_id == project_id)
                    & (NetworkLink.right_network_name == network_name)
                ),
            ),
        )
    )
    return list(result.scalars().all())


async def assert_network_deletable(
    session: AsyncSession,
    proxy: AgentProxy,
    project: Project,
    *,
    agent_id: str,
    network_name: str,
    agent_network_exists: bool = True,
) -> None:
    """Raise HTTP 409 if VMs, topology links, or active breakout block deletion."""
    links = await _active_links_for_endpoint(
        session,
        project.organization_id,
        agent_id=agent_id,
        project_id=project.id,
        network_name=network_name,
    )
    if links:
        names = ", ".join(link.name for link in links[:3])
        extra = f" (+{len(links) - 3} more)" if len(links) > 3 else ""
        raise HTTPException(
            status_code=409,
            detail=(
                f"Cannot delete network '{network_name}': "
                f"{len(links)} topology link(s) still connected ({names}{extra}). "
                "Remove the link(s) in Topology first."
            ),
        )

    if not agent_network_exists:
        return

    vm_names = await _vms_using_network(
        proxy,
        agent_id=agent_id,
        organization_id=project.organization_id,
        network_name=network_name,
    )
    if vm_names:
        sample = ", ".join(vm_names[:5])
        extra = f" (+{len(vm_names) - 5} more)" if len(vm_names) > 5 else ""
        raise HTTPException(
            status_code=409,
            detail=(
                f"Cannot delete network '{network_name}': "
                f"{len(vm_names)} VM(s) still use it ({sample}{extra}). "
                "Move or delete those VMs first."
            ),
        )

    try:
        breakout = await proxy.get_breakout(
            agent_id, project.organization_id, network_name
        )
    except HTTPException as exc:
        if exc.status_code == 404:
            return
        raise
    if _breakout_is_active(breakout):
        raise HTTPException(
            status_code=409,
            detail=(
                f"Cannot delete network '{network_name}': "
                "breakout configuration is still active. "
                "Disable WireGuard or flat breakout on this network first."
            ),
        )
