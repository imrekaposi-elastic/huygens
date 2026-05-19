"""Proxied libvirt agent operator APIs."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Query

from huy_projects.api.deps import AgentProxyDep, CurrentUserDep, ReadableProjectDep, SessionDep
from huy_projects.services import authorization, desired_state

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
    body: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    authorization.require_project_operate(user, project)
    result = await proxy.create_network(agent_id, project.organization_id, body)
    await desired_state.upsert_desired_state(
        session,
        project_id=project.id,
        agent_id=agent_id,
        resource_type="network",
        name=result["name"],
        desired_state=body,
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
    await desired_state.clear_desired_state(
        session,
        project_id=project.id,
        agent_id=agent_id,
        resource_type="network",
        name=name,
    )
