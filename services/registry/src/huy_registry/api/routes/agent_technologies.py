"""Supported agent technologies (libvirt-agent, …)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from huy_registry.api.deps import PlatformAdminDep, SessionDep
from huy_registry.schemas import AgentTechnologyOut, AgentTechnologyUpdate
from huy_registry.services import agent_technology_service

router = APIRouter(prefix="/api/v1/agent-technologies", tags=["agent-technologies"])


@router.get("", response_model=list[AgentTechnologyOut])
async def list_agent_technologies(
    _admin: PlatformAdminDep,
    session: SessionDep,
) -> list[AgentTechnologyOut]:
    rows = await agent_technology_service.list_agent_technologies(session)
    return [AgentTechnologyOut.model_validate(r) for r in rows]


@router.patch("/{technology_id}", response_model=AgentTechnologyOut)
async def update_agent_technology(
    technology_id: str,
    body: AgentTechnologyUpdate,
    _admin: PlatformAdminDep,
    session: SessionDep,
) -> AgentTechnologyOut:
    row = await agent_technology_service.get_agent_technology(session, technology_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Agent technology not found")
    if body.platform_enabled is False and await agent_technology_service.technology_in_use(
        session, technology_id
    ):
        raise HTTPException(
            status_code=409,
            detail="Cannot disable technology while agents are still enrolled",
        )
    updated = await agent_technology_service.update_agent_technology(session, row, body)
    return AgentTechnologyOut.model_validate(updated)
