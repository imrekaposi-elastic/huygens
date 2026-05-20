"""Proxied libvirt agent cloud-init profile APIs."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body

from huy_projects.api.deps import AgentProxyDep, CurrentUserDep, ReadableProjectDep
from huy_projects.services import authorization

router = APIRouter(
    prefix="/api/v1/projects/{project_id}/agents/{agent_id}/cloud-init",
    tags=["cloud-init"],
)


@router.get("", response_model=list[dict[str, Any]])
async def list_cloud_init_profiles(
    project: ReadableProjectDep,
    agent_id: str,
    user: CurrentUserDep,
    proxy: AgentProxyDep,
) -> list[dict[str, Any]]:
    authorization.require_project_read(user, project)
    return await proxy.list_cloud_init_profiles(agent_id, project.organization_id)


@router.post("/validate", response_model=dict[str, Any])
async def validate_cloud_init(
    project: ReadableProjectDep,
    agent_id: str,
    user: CurrentUserDep,
    proxy: AgentProxyDep,
    body: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    authorization.require_project_read(user, project)
    return await proxy.validate_cloud_init(agent_id, project.organization_id, body)


@router.get("/{name}", response_model=dict[str, Any])
async def get_cloud_init_profile(
    project: ReadableProjectDep,
    agent_id: str,
    name: str,
    user: CurrentUserDep,
    proxy: AgentProxyDep,
) -> dict[str, Any]:
    authorization.require_project_read(user, project)
    return await proxy.get_cloud_init_profile(agent_id, project.organization_id, name)


@router.post("", response_model=dict[str, Any], status_code=201)
async def create_cloud_init_profile(
    project: ReadableProjectDep,
    agent_id: str,
    user: CurrentUserDep,
    proxy: AgentProxyDep,
    body: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    authorization.require_project_operate(user, project)
    return await proxy.create_cloud_init_profile(agent_id, project.organization_id, body)


@router.patch("/{name}", response_model=dict[str, Any])
async def update_cloud_init_profile(
    project: ReadableProjectDep,
    agent_id: str,
    name: str,
    user: CurrentUserDep,
    proxy: AgentProxyDep,
    body: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    authorization.require_project_operate(user, project)
    return await proxy.update_cloud_init_profile(
        agent_id, project.organization_id, name, body
    )


@router.delete("/{name}", status_code=204)
async def delete_cloud_init_profile(
    project: ReadableProjectDep,
    agent_id: str,
    name: str,
    user: CurrentUserDep,
    proxy: AgentProxyDep,
) -> None:
    authorization.require_project_operate(user, project)
    await proxy.delete_cloud_init_profile(agent_id, project.organization_id, name)
