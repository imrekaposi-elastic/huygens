"""Agent info endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from huy_libvirt_agent import __version__
from huy_libvirt_agent.api.deps import StateDep, verify_token
from huy_libvirt_agent.api.schemas.agent import AgentLabels, AgentSettingsResponse

router = APIRouter(
    prefix="/api/v1/agent",
    tags=["agent"],
    dependencies=[Depends(verify_token)],
)


@router.get(
    "",
    response_model=AgentSettingsResponse,
    summary="Get agent identity and settings",
)
async def get_agent(state: StateDep) -> AgentSettingsResponse:
    return AgentSettingsResponse(
        hostname=state.hostname,
        version=__version__,
        settings=AgentLabels(**state.settings.agent_labels),
        libvirt_uri=state.settings.libvirt_uri,
        data_dir=str(state.settings.data_dir),
    )
