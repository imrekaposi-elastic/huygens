"""Proxied libvirt agent breakout APIs (Phase 6)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body

from huy_projects.api.deps import AgentProxyDep, CurrentUserDep, ReadableProjectDep, SessionDep
from huy_projects.services import authorization, project_scope

router = APIRouter(
    prefix="/api/v1/projects/{project_id}/agents/{agent_id}/networks/{name}",
    tags=["agent-proxy-breakout"],
)


@router.get("/breakout", response_model=dict[str, Any])
async def get_breakout(
    project: ReadableProjectDep,
    agent_id: str,
    name: str,
    user: CurrentUserDep,
    proxy: AgentProxyDep,
    session: SessionDep,
) -> dict[str, Any]:
    authorization.require_project_read(user, project)
    await project_scope.require_resource_in_project(
        session, project, agent_id=agent_id, resource_type="network", name=name
    )
    return await proxy.get_breakout(agent_id, project.organization_id, name)


@router.put("/breakout/wireguard", response_model=dict[str, Any])
async def put_wireguard_breakout(
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
        session, project, agent_id=agent_id, resource_type="network", name=name
    )
    return await proxy.put_wireguard_breakout(agent_id, project.organization_id, name, body)


@router.put("/breakout/flat", response_model=dict[str, Any])
async def put_flat_breakout(
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
        session, project, agent_id=agent_id, resource_type="network", name=name
    )
    return await proxy.put_flat_breakout(agent_id, project.organization_id, name, body)
