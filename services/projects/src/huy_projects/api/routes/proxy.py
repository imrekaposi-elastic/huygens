"""Proxied libvirt agent operator APIs."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, HTTPException, Query

from huy_projects.api.deps import AgentProxyDep, CurrentUserDep, ReadableProjectDep, SessionDep, SettingsDep
from huy_projects.schemas import ResourceAssignRequest, ResourceAssignmentOut
from huy_projects.libvirt_system import is_system_network
from huy_projects.services import authorization, desired_state, ipam_service, resource_assignment_service

router = APIRouter(prefix="/api/v1/projects/{project_id}/agents/{agent_id}", tags=["agent-proxy"])


@router.get("/vms", response_model=list[dict[str, Any]])
async def list_vms(
    project: ReadableProjectDep,
    agent_id: str,
    user: CurrentUserDep,
    proxy: AgentProxyDep,
) -> list[dict[str, Any]]:
    authorization.require_project_read(user, project)
    return await proxy.list_vms(agent_id, project.organization_id)


@router.get("/vms/{name}", response_model=dict[str, Any])
async def get_vm(
    project: ReadableProjectDep,
    agent_id: str,
    name: str,
    user: CurrentUserDep,
    proxy: AgentProxyDep,
) -> dict[str, Any]:
    authorization.require_project_read(user, project)
    return await proxy.get_vm(agent_id, project.organization_id, name)


@router.post("/vms", response_model=dict[str, Any], status_code=201)
async def create_vm(
    project: ReadableProjectDep,
    agent_id: str,
    user: CurrentUserDep,
    proxy: AgentProxyDep,
    session: SessionDep,
    body: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    authorization.require_project_operate(user, project)
    result = await proxy.create_vm(agent_id, project.organization_id, body)
    await desired_state.upsert_desired_state(
        session,
        project_id=project.id,
        agent_id=agent_id,
        resource_type="vm",
        name=result["name"],
        desired_state=body,
    )
    return result


@router.patch("/vms/{name}", response_model=dict[str, Any])
async def patch_vm(
    project: ReadableProjectDep,
    agent_id: str,
    name: str,
    user: CurrentUserDep,
    proxy: AgentProxyDep,
    session: SessionDep,
    body: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    authorization.require_project_operate(user, project)
    result = await proxy.patch_vm(agent_id, project.organization_id, name, body)
    existing = await proxy.get_vm(agent_id, project.organization_id, name)
    await desired_state.upsert_desired_state(
        session,
        project_id=project.id,
        agent_id=agent_id,
        resource_type="vm",
        name=name,
        desired_state={**existing, **body},
    )
    return result


@router.delete("/vms/{name}", status_code=204)
async def delete_vm(
    project: ReadableProjectDep,
    agent_id: str,
    name: str,
    user: CurrentUserDep,
    proxy: AgentProxyDep,
    session: SessionDep,
) -> None:
    authorization.require_project_operate(user, project)
    await proxy.delete_vm(agent_id, project.organization_id, name)
    await desired_state.clear_desired_state(
        session,
        project_id=project.id,
        agent_id=agent_id,
        resource_type="vm",
        name=name,
    )


@router.get("/networks", response_model=list[dict[str, Any]])
async def list_networks(
    project: ReadableProjectDep,
    agent_id: str,
    user: CurrentUserDep,
    proxy: AgentProxyDep,
) -> list[dict[str, Any]]:
    authorization.require_project_read(user, project)
    return await proxy.list_networks(agent_id, project.organization_id)


@router.get("/networks/{name}", response_model=dict[str, Any])
async def get_network(
    project: ReadableProjectDep,
    agent_id: str,
    name: str,
    user: CurrentUserDep,
    proxy: AgentProxyDep,
) -> dict[str, Any]:
    authorization.require_project_read(user, project)
    return await proxy.get_network(agent_id, project.organization_id, name)


@router.post("/networks", response_model=dict[str, Any], status_code=201)
async def create_network(
    project: ReadableProjectDep,
    agent_id: str,
    user: CurrentUserDep,
    proxy: AgentProxyDep,
    session: SessionDep,
    settings: SettingsDep,
    body: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    authorization.require_project_operate(user, project)
    raw = dict(body)
    ipam_bypass = raw.get("ipam_bypass") is True and user.is_platform_admin()
    has_ipam = "ipam" in raw or "allocation_id" in raw
    has_manual_cidr = "ipv4_cidr" in raw and not has_ipam

    if settings.ipam_enforce and has_manual_cidr and not ipam_bypass:
        raise HTTPException(
            status_code=400,
            detail="ipv4_cidr must come from IPAM; set ipam.pool_id+hosts or allocation_id",
        )

    agent_body, allocation = await ipam_service.resolve_network_cidr(session, project, raw)
    if "ipv4_cidr" not in agent_body:
        raise HTTPException(
            status_code=400,
            detail="Missing ipv4_cidr; provide ipam, allocation_id, or ipam_bypass (platform_admin)",
        )

    result = await proxy.create_network(agent_id, project.organization_id, agent_body)
    if allocation is not None:
        await ipam_service.bind_allocation_to_network(session, allocation, result["name"])
    await desired_state.upsert_desired_state(
        session,
        project_id=project.id,
        agent_id=agent_id,
        resource_type="network",
        name=result["name"],
        desired_state={**raw, "ipv4_cidr": agent_body["ipv4_cidr"]},
    )
    return result


@router.patch("/networks/{name}", response_model=dict[str, Any])
async def patch_network(
    project: ReadableProjectDep,
    agent_id: str,
    name: str,
    user: CurrentUserDep,
    proxy: AgentProxyDep,
    session: SessionDep,
    body: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    authorization.require_project_operate(user, project)
    result = await proxy.patch_network(agent_id, project.organization_id, name, body)
    existing = await proxy.get_network(agent_id, project.organization_id, name)
    await desired_state.upsert_desired_state(
        session,
        project_id=project.id,
        agent_id=agent_id,
        resource_type="network",
        name=name,
        desired_state={**existing, **body},
    )
    return result


@router.delete("/networks/{name}", status_code=204)
async def delete_network(
    project: ReadableProjectDep,
    agent_id: str,
    name: str,
    user: CurrentUserDep,
    proxy: AgentProxyDep,
    session: SessionDep,
    purge: bool = Query(False),
) -> None:
    authorization.require_project_operate(user, project)
    await proxy.delete_network(
        agent_id, project.organization_id, name, purge=purge
    )
    from sqlalchemy import select

    from huy_projects.models import IpAllocation

    result = await session.execute(
        select(IpAllocation).where(
            IpAllocation.project_id == project.id,
            IpAllocation.network_name == name,
            IpAllocation.status == "allocated",
        )
    )
    for row in result.scalars().all():
        await ipam_service.release_allocation(session, row)
    await desired_state.clear_desired_state(
        session,
        project_id=project.id,
        agent_id=agent_id,
        resource_type="network",
        name=name,
    )


@router.post("/assignments", response_model=ResourceAssignmentOut, status_code=201)
async def assign_existing_resource(
    project: ReadableProjectDep,
    agent_id: str,
    body: ResourceAssignRequest,
    user: CurrentUserDep,
    proxy: AgentProxyDep,
    session: SessionDep,
) -> ResourceAssignmentOut:
    """Adopt an existing agent VM or network into this project (inventory orphan → managed)."""
    authorization.require_project_operate(user, project)
    if body.resource_type == "network" and is_system_network(body.name):
        raise HTTPException(
            status_code=400,
            detail=f"Network '{body.name}' is a system network and cannot be assigned to a project",
        )
    try:
        if body.resource_type == "vm":
            actual = await proxy.get_vm(agent_id, project.organization_id, body.name)
        else:
            actual = await proxy.get_network(agent_id, project.organization_id, body.name)
    except HTTPException as exc:
        if exc.status_code == 404:
            raise HTTPException(
                status_code=404,
                detail=f"No {body.resource_type} '{body.name}' on this agent",
            ) from exc
        raise
    return await resource_assignment_service.assign_resource(
        session,
        project,
        agent_id=agent_id,
        resource_type=body.resource_type,
        name=body.name,
        actual_state=actual,
    )


@router.delete("/assignments/{resource_type}/{name}", status_code=204)
async def unassign_resource(
    project: ReadableProjectDep,
    agent_id: str,
    resource_type: str,
    name: str,
    user: CurrentUserDep,
    session: SessionDep,
) -> None:
    """Remove project membership without deleting the resource on the agent."""
    authorization.require_project_operate(user, project)
    if resource_type not in ("vm", "network"):
        raise HTTPException(status_code=400, detail="resource_type must be vm or network")
    await resource_assignment_service.unassign_resource(
        session,
        project,
        agent_id=agent_id,
        resource_type=resource_type,  # type: ignore[arg-type]
        name=name,
    )
