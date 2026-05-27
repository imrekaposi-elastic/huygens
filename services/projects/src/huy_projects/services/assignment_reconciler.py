"""Prune stale project network assignments when the agent no longer has the vnet."""

from __future__ import annotations

import structlog
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from huy_projects.libvirt_system import is_system_network
from huy_projects.models import IpAllocation, Project, ProjectResource
from huy_projects.services import desired_state, ipam_service
from huy_projects.services.agent_proxy import AgentProxy

logger = structlog.get_logger(__name__)


async def reconcile_stale_network_assignments(
    session: AsyncSession,
    *,
    proxy: AgentProxy,
) -> int:
    """Return count of assignments removed."""
    result = await session.execute(
        select(ProjectResource, Project.organization_id)
        .join(Project, Project.id == ProjectResource.project_id)
        .where(ProjectResource.resource_type == "network")
    )
    rows = result.all()
    by_agent: dict[tuple[str, str], list[ProjectResource]] = {}
    for resource, organization_id in rows:
        if is_system_network(resource.name):
            continue
        key = (organization_id, resource.agent_id)
        by_agent.setdefault(key, []).append(resource)

    removed = 0
    for (organization_id, agent_id), resources in by_agent.items():
        try:
            networks = await proxy.list_networks(agent_id, organization_id)
        except HTTPException as exc:
            logger.warning(
                "assignment_reconcile_agent_unreachable",
                agent_id=agent_id,
                status=exc.status_code,
            )
            continue
        names = {n.get("name") for n in networks if n.get("name")}
        for resource in resources:
            if resource.name in names:
                continue
            await _remove_stale_assignment(session, resource)
            removed += 1
            logger.info(
                "stale_network_assignment_removed",
                agent_id=agent_id,
                project_id=resource.project_id,
                network_name=resource.name,
            )

    if removed:
        await session.commit()
    return removed


async def _remove_stale_assignment(session: AsyncSession, resource: ProjectResource) -> None:
    alloc_result = await session.execute(
        select(IpAllocation).where(
            IpAllocation.project_id == resource.project_id,
            IpAllocation.network_name == resource.name,
            IpAllocation.status == "allocated",
        )
    )
    for row in alloc_result.scalars().all():
        await ipam_service.release_allocation(session, row)
    await desired_state.clear_desired_state(
        session,
        project_id=resource.project_id,
        agent_id=resource.agent_id,
        resource_type="network",
        name=resource.name,
    )
