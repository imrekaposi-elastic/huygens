from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException

from huy_auth.agent_tokens import decrypt_agent_token
from huy_auth.roles import PERM_INVENTORY_READ
from huy_registry.api.deps import (
    AgentExportDep,
    AgentRegisterDep,
    CurrentUserDep,
    PlatformAdminDep,
    SessionDep,
    SettingsDep,
)
from huy_registry.schemas import (
    AgentCreate,
    AgentCreated,
    AgentOut,
    AgentTokenExport,
    AgentUpdate,
)
from huy_registry.services import agent_service, connection_probe
from huy_registry.services.agent_service import agent_to_out

router = APIRouter(prefix="/api/v1/agents", tags=["agents"])


def _filter_agents(user, agents):
    if user.is_platform_admin():
        return agents
    allowed_orgs = {m.organization_id for m in user.org_memberships}
    return [a for a in agents if a.organization_id in allowed_orgs]


async def _probe_and_update(session, settings, agent, token: str):
    ok, err = await connection_probe.probe_agent(agent.base_url, token, tls_verify=agent.tls_verify)
    return await agent_service.update_poll_status(
        session,
        agent,
        connection_status="connected" if ok else "error",
        last_seen_at=datetime.now(UTC) if ok else agent.last_seen_at,
        last_poll_error=err,
    )


@router.post("", response_model=AgentCreated, status_code=201)
async def register_agent(
    body: AgentCreate,
    _admin: PlatformAdminDep,
    session: SessionDep,
    settings: SettingsDep,
) -> AgentCreated:
    agent, token = await agent_service.create_agent(session, settings, body)
    agent = await _probe_and_update(session, settings, agent, token)
    out = agent_to_out(agent)
    return AgentCreated(**out.model_dump(), agent_token=token)


@router.get("", response_model=list[AgentOut])
async def list_agents(user: CurrentUserDep, session: SessionDep) -> list[AgentOut]:
    if not user.has_permission(PERM_INVENTORY_READ):
        raise HTTPException(status_code=403, detail="Permission denied")
    if user.is_platform_admin():
        agents = await agent_service.list_agents(session)
    else:
        by_id: dict[str, object] = {}
        for m in user.org_memberships:
            for agent in await agent_service.list_agents(session, organization_id=m.organization_id):
                by_id[agent.id] = agent
        agents = list(by_id.values())
    return [agent_to_out(a) for a in _filter_agents(user, agents)]  # type: ignore[arg-type]


@router.get("/{agent_id}", response_model=AgentOut)
async def get_agent(agent_id: str, user: CurrentUserDep, session: SessionDep) -> AgentOut:
    if not user.has_permission(PERM_INVENTORY_READ):
        raise HTTPException(status_code=403, detail="Permission denied")
    agent = await agent_service.get_agent(session, agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    if not user.is_platform_admin() and not user.can_access_org(agent.organization_id):
        raise HTTPException(status_code=403, detail="Access denied")
    return agent_to_out(agent)


@router.delete("/{agent_id}", status_code=204)
async def delete_agent(
    agent_id: str,
    _admin: PlatformAdminDep,
    session: SessionDep,
    settings: SettingsDep,
) -> None:
    agent = await agent_service.get_agent(session, agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    await agent_service.delete_agent(session, settings, agent)


@router.patch("/{agent_id}", response_model=AgentOut)
async def patch_agent(
    agent_id: str,
    body: AgentUpdate,
    _user: AgentRegisterDep,
    session: SessionDep,
) -> AgentOut:
    agent = await agent_service.get_agent(session, agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    updated = await agent_service.update_agent(session, agent, body)
    return agent_to_out(updated)


@router.post("/{agent_id}/export-token", response_model=AgentTokenExport)
async def export_agent_token(
    agent_id: str,
    _user: AgentExportDep,
    session: SessionDep,
    settings: SettingsDep,
) -> AgentTokenExport:
    agent = await agent_service.get_agent(session, agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    token = await agent_service.export_token(session, settings, agent)
    return AgentTokenExport(agent_token=token)


@router.post("/{agent_id}/rotate-token", response_model=AgentTokenExport)
async def rotate_agent_token(
    agent_id: str,
    _user: AgentExportDep,
    session: SessionDep,
    settings: SettingsDep,
) -> AgentTokenExport:
    agent = await agent_service.get_agent(session, agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    token = await agent_service.rotate_token(session, settings, agent)
    return AgentTokenExport(agent_token=token)


@router.post("/{agent_id}/test-connection", response_model=AgentOut)
async def test_connection(
    agent_id: str,
    _user: AgentRegisterDep,
    session: SessionDep,
    settings: SettingsDep,
) -> AgentOut:
    agent = await agent_service.get_agent(session, agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    token = decrypt_agent_token(agent.token_encrypted, settings.agent_token_encryption_key)
    updated = await _probe_and_update(session, settings, agent, token)
    return agent_to_out(updated)
