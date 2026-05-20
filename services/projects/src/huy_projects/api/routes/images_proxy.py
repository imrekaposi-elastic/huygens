"""Proxied libvirt agent managed image APIs."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body

from huy_projects.api.deps import AgentProxyDep, CurrentUserDep, ReadableProjectDep
from huy_projects.services import authorization

router = APIRouter(
    prefix="/api/v1/projects/{project_id}/agents/{agent_id}/images",
    tags=["images"],
)


@router.get("", response_model=list[dict[str, Any]])
async def list_images(
    project: ReadableProjectDep,
    agent_id: str,
    user: CurrentUserDep,
    proxy: AgentProxyDep,
) -> list[dict[str, Any]]:
    authorization.require_project_read(user, project)
    return await proxy.list_images(agent_id, project.organization_id)


@router.get("/{name}", response_model=dict[str, Any])
async def get_image(
    project: ReadableProjectDep,
    agent_id: str,
    name: str,
    user: CurrentUserDep,
    proxy: AgentProxyDep,
) -> dict[str, Any]:
    authorization.require_project_read(user, project)
    return await proxy.get_image(agent_id, project.organization_id, name)


@router.post("", response_model=dict[str, Any], status_code=201)
async def create_image(
    project: ReadableProjectDep,
    agent_id: str,
    user: CurrentUserDep,
    proxy: AgentProxyDep,
    body: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    authorization.require_project_operate(user, project)
    return await proxy.create_image(agent_id, project.organization_id, body)


@router.patch("/{name}", response_model=dict[str, Any])
async def update_image(
    project: ReadableProjectDep,
    agent_id: str,
    name: str,
    user: CurrentUserDep,
    proxy: AgentProxyDep,
    body: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    authorization.require_project_operate(user, project)
    return await proxy.update_image(agent_id, project.organization_id, name, body)


@router.delete("/{name}", status_code=204)
async def delete_image(
    project: ReadableProjectDep,
    agent_id: str,
    name: str,
    user: CurrentUserDep,
    proxy: AgentProxyDep,
) -> None:
    authorization.require_project_operate(user, project)
    await proxy.delete_image(agent_id, project.organization_id, name)
