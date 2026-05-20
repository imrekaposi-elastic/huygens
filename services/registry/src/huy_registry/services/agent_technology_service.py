"""Agent technology catalog."""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from huy_registry.models import Agent, AgentTechnology
from huy_registry.schemas import AgentTechnologyUpdate


async def list_agent_technologies(session: AsyncSession) -> list[AgentTechnology]:
    result = await session.execute(select(AgentTechnology).order_by(AgentTechnology.name))
    return list(result.scalars().all())


async def get_agent_technology(session: AsyncSession, technology_id: str) -> AgentTechnology | None:
    return await session.get(AgentTechnology, technology_id)


async def get_by_slug(session: AsyncSession, slug: str) -> AgentTechnology | None:
    result = await session.execute(select(AgentTechnology).where(AgentTechnology.slug == slug))
    return result.scalar_one_or_none()


async def update_agent_technology(
    session: AsyncSession, row: AgentTechnology, body: AgentTechnologyUpdate
) -> AgentTechnology:
    if body.platform_enabled is not None:
        row.platform_enabled = body.platform_enabled
    if body.name is not None:
        row.name = body.name
    if body.description is not None:
        row.description = body.description
    await session.commit()
    await session.refresh(row)
    return row


async def require_enabled_technology(session: AsyncSession, technology_id: str) -> AgentTechnology:
    row = await get_agent_technology(session, technology_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Agent technology not found")
    if not row.platform_enabled:
        raise HTTPException(status_code=400, detail="Agent technology is disabled platform-wide")
    return row


async def technology_in_use(session: AsyncSession, technology_id: str) -> bool:
    result = await session.execute(
        select(Agent.id).where(Agent.agent_technology_id == technology_id).limit(1)
    )
    return result.scalar_one_or_none() is not None
