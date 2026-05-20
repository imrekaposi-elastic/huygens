"""Agent enrollment and token vault."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from huy_auth.agent_tokens import (
    decrypt_agent_token,
    encrypt_agent_token,
    generate_agent_token,
    hash_agent_token,
)
from huy_registry.config import Settings
from huy_registry.models import Agent, InfrastructureProvider, Region
from huy_registry.schemas import AgentConnectOut, AgentCreate, AgentOut, AgentUpdate, PollTargetOut
from huy_registry.services import agent_technology_service


def agent_to_out(agent: Agent) -> AgentOut:
    return AgentOut(
        id=agent.id,
        name=agent.name,
        base_url=agent.base_url,
        organization_id=agent.organization_id,
        infrastructure_provider_id=agent.infrastructure_provider_id,
        region_id=agent.region_id,
        agent_technology_id=agent.agent_technology_id,
        agent_technology_slug=agent.agent_technology.slug,
        refresh_seconds=agent.refresh_seconds,
        tls_verify=agent.tls_verify,
        connection_status=agent.connection_status,  # type: ignore[arg-type]
        last_seen_at=agent.last_seen_at,
        last_poll_error=agent.last_poll_error,
        token_exported=agent.token_exported_at is not None,
        created_at=agent.created_at,
        updated_at=agent.updated_at,
    )


async def get_agent(session: AsyncSession, agent_id: str) -> Agent | None:
    result = await session.execute(
        select(Agent)
        .where(Agent.id == agent_id)
        .options(selectinload(Agent.region), selectinload(Agent.agent_technology))
    )
    return result.scalar_one_or_none()


async def list_agents(session: AsyncSession, organization_id: str | None = None) -> list[Agent]:
    stmt = (
        select(Agent)
        .order_by(Agent.name)
        .options(selectinload(Agent.agent_technology))
    )
    if organization_id is not None:
        stmt = stmt.where(Agent.organization_id == organization_id)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def create_agent(session: AsyncSession, settings: Settings, body: AgentCreate) -> tuple[Agent, str]:
    provider = await session.get(InfrastructureProvider, body.infrastructure_provider_id)
    if provider is None:
        raise HTTPException(status_code=400, detail="Unknown infrastructure_provider_id")
    region = await session.get(Region, body.region_id)
    if region is None or region.infrastructure_provider_id != body.infrastructure_provider_id:
        raise HTTPException(status_code=400, detail="Unknown region_id for infrastructure provider")
    technology = await agent_technology_service.require_enabled_technology(
        session, body.agent_technology_id
    )

    existing = await session.execute(select(Agent).where(Agent.name == body.name))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="Agent name already exists")

    token = generate_agent_token()
    refresh = body.refresh_seconds or settings.default_refresh_seconds
    agent = Agent(
        name=body.name,
        base_url=str(body.base_url).rstrip("/"),
        organization_id=body.organization_id,
        infrastructure_provider_id=body.infrastructure_provider_id,
        region_id=body.region_id,
        agent_technology_id=technology.id,
        token_hash=hash_agent_token(token),
        token_encrypted=encrypt_agent_token(token, settings.agent_token_encryption_key),
        refresh_seconds=refresh,
        tls_verify=body.tls_verify,
        connection_status="pending",
    )
    session.add(agent)
    await session.commit()
    await session.refresh(agent, attribute_names=["agent_technology"])
    return agent, token


async def delete_agent(session: AsyncSession, settings: Settings, agent: Agent) -> None:
    agent_id = agent.id
    await session.delete(agent)
    await session.commit()
    from huy_registry.services.inventory_client import delete_agent_snapshot

    await delete_agent_snapshot(settings, agent_id)


async def update_agent(session: AsyncSession, agent: Agent, body: AgentUpdate) -> Agent:
    if body.base_url is not None:
        agent.base_url = str(body.base_url).rstrip("/")
    if body.organization_id is not None:
        agent.organization_id = body.organization_id
    if body.refresh_seconds is not None:
        agent.refresh_seconds = body.refresh_seconds
    if body.tls_verify is not None:
        agent.tls_verify = body.tls_verify
    if body.connection_status is not None:
        agent.connection_status = body.connection_status
    agent.updated_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(agent, attribute_names=["agent_technology"])
    return agent


async def export_token(session: AsyncSession, settings: Settings, agent: Agent) -> str:
    if agent.token_exported_at is not None:
        raise HTTPException(status_code=409, detail="Agent token was already exported")
    token = decrypt_agent_token(agent.token_encrypted, settings.agent_token_encryption_key)
    agent.token_exported_at = datetime.now(UTC)
    await session.commit()
    return token


async def rotate_token(session: AsyncSession, settings: Settings, agent: Agent) -> str:
    token = generate_agent_token()
    agent.token_hash = hash_agent_token(token)
    agent.token_encrypted = encrypt_agent_token(token, settings.agent_token_encryption_key)
    agent.token_exported_at = None
    agent.updated_at = datetime.now(UTC)
    await session.commit()
    return token


async def get_agent_connect(
    session: AsyncSession, settings: Settings, agent_id: str
) -> AgentConnectOut | None:
    agent = await get_agent(session, agent_id)
    if agent is None:
        return None
    token = decrypt_agent_token(agent.token_encrypted, settings.agent_token_encryption_key)
    return AgentConnectOut(
        agent_id=agent.id,
        organization_id=agent.organization_id,
        base_url=agent.base_url,
        agent_token=token,
        tls_verify=agent.tls_verify,
    )


async def list_poll_targets(session: AsyncSession, settings: Settings) -> list[PollTargetOut]:
    agents = await list_agents(session)
    targets: list[PollTargetOut] = []
    for agent in agents:
        token = decrypt_agent_token(agent.token_encrypted, settings.agent_token_encryption_key)
        targets.append(
            PollTargetOut(
                agent_id=agent.id,
                name=agent.name,
                organization_id=agent.organization_id,
                region_id=agent.region_id,
                agent_technology_id=agent.agent_technology_id,
                base_url=agent.base_url,
                agent_token=token,
                refresh_seconds=agent.refresh_seconds,
                tls_verify=agent.tls_verify,
                connection_status=agent.connection_status,  # type: ignore[arg-type]
            )
        )
    return targets


async def update_poll_status(
    session: AsyncSession,
    agent: Agent,
    *,
    connection_status: str,
    last_seen_at: datetime | None,
    last_poll_error: str | None,
) -> Agent:
    agent.connection_status = connection_status
    agent.last_seen_at = last_seen_at
    agent.last_poll_error = last_poll_error
    agent.updated_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(agent, attribute_names=["agent_technology"])
    return agent
