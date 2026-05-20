from datetime import datetime

from fastapi import APIRouter, HTTPException

from huy_registry.api.deps import InventoryServiceDep, SessionDep, SettingsDep
from huy_registry.schemas import AgentConnectOut, AgentTechnologyOut, PollStatusUpdate, PollTargetOut
from huy_registry.services import agent_service, agent_technology_service

router = APIRouter(prefix="/api/v1/internal", tags=["internal"])


@router.get("/agent-technologies", response_model=list[AgentTechnologyOut])
async def list_agent_technologies_internal(
    _service: InventoryServiceDep,
    session: SessionDep,
) -> list[AgentTechnologyOut]:
    rows = await agent_technology_service.list_agent_technologies(session)
    return [AgentTechnologyOut.model_validate(r) for r in rows]


@router.get("/poll-targets", response_model=list[PollTargetOut])
async def poll_targets(
    _service: InventoryServiceDep,
    session: SessionDep,
    settings: SettingsDep,
) -> list[PollTargetOut]:
    return await agent_service.list_poll_targets(session, settings)


@router.get("/agents/{agent_id}/connect", response_model=AgentConnectOut)
async def agent_connect(
    agent_id: str,
    _service: InventoryServiceDep,
    session: SessionDep,
    settings: SettingsDep,
) -> AgentConnectOut:
    info = await agent_service.get_agent_connect(session, settings, agent_id)
    if info is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return info


@router.patch("/agents/{agent_id}/poll-status", status_code=204)
async def update_poll_status(
    agent_id: str,
    body: PollStatusUpdate,
    _service: InventoryServiceDep,
    session: SessionDep,
) -> None:
    agent = await agent_service.get_agent(session, agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    await agent_service.update_poll_status(
        session,
        agent,
        connection_status=body.connection_status,
        last_seen_at=body.last_seen_at,
        last_poll_error=body.last_poll_error,
    )
