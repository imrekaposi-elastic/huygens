"""Proxied libvirt agent cloud-init profile APIs."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body

from huy_projects.api.deps import AgentProxyDep, CurrentUserDep, ReadableProjectDep, SessionDep
from huy_projects.services import authorization, desired_state, project_scope

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
    session: SessionDep,
) -> list[dict[str, Any]]:
    authorization.require_project_read(user, project)
    all_profiles = await proxy.list_cloud_init_profiles(agent_id, project.organization_id)
    return await project_scope.filter_agent_list(
        session,
        project,
        agent_id=agent_id,
        resource_type="cloud_init",
        items=all_profiles,
    )


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
    session: SessionDep,
) -> dict[str, Any]:
    authorization.require_project_read(user, project)
    await project_scope.require_resource_in_project(
        session, project, agent_id=agent_id, resource_type="cloud_init", name=name
    )
    return await proxy.get_cloud_init_profile(agent_id, project.organization_id, name)


@router.post("", response_model=dict[str, Any], status_code=201)
async def create_cloud_init_profile(
    project: ReadableProjectDep,
    agent_id: str,
    user: CurrentUserDep,
    proxy: AgentProxyDep,
    session: SessionDep,
    body: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    authorization.require_project_operate(user, project)
    result = await proxy.create_cloud_init_profile(agent_id, project.organization_id, body)
    profile_name = str(result.get("name") or body.get("name") or "")
    if profile_name:
        await desired_state.upsert_desired_state(
            session,
            project_id=project.id,
            agent_id=agent_id,
            resource_type="cloud_init",
            name=profile_name,
            desired_state=body,
        )
    return result


@router.patch("/{name}", response_model=dict[str, Any])
async def update_cloud_init_profile(
    project: ReadableProjectDep,
    agent_id: str,
    name: str,
    user: CurrentUserDep,
    proxy: AgentProxyDep,
    session: SessionDep,
    body: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    authorization.require_project_operate(user, project)
    await project_scope.require_resource_in_project(
        session, project, agent_id=agent_id, resource_type="cloud_init", name=name
    )
    result = await proxy.update_cloud_init_profile(
        agent_id, project.organization_id, name, body
    )
    existing = await proxy.get_cloud_init_profile(agent_id, project.organization_id, name)
    await desired_state.upsert_desired_state(
        session,
        project_id=project.id,
        agent_id=agent_id,
        resource_type="cloud_init",
        name=name,
        desired_state={**existing, **body},
    )
    return result


@router.delete("/{name}", status_code=204)
async def delete_cloud_init_profile(
    project: ReadableProjectDep,
    agent_id: str,
    name: str,
    user: CurrentUserDep,
    proxy: AgentProxyDep,
    session: SessionDep,
) -> None:
    authorization.require_project_operate(user, project)
    await project_scope.require_resource_in_project(
        session, project, agent_id=agent_id, resource_type="cloud_init", name=name
    )
    await proxy.delete_cloud_init_profile(agent_id, project.organization_id, name)
    await desired_state.clear_desired_state(
        session,
        project_id=project.id,
        agent_id=agent_id,
        resource_type="cloud_init",
        name=name,
    )
