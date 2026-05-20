"""Seed built-in agent technologies."""

from __future__ import annotations

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from huy_registry.models import AgentTechnology

logger = structlog.get_logger(__name__)

BUILTIN_TECHNOLOGIES = (
    {
        "slug": "libvirt-agent",
        "name": "Libvirt agent",
        "description": "Collects VM and network inventory from libvirt/KVM hypervisors.",
    },
)


async def bootstrap_agent_technologies(session: AsyncSession) -> None:
    for spec in BUILTIN_TECHNOLOGIES:
        existing = await session.scalar(
            select(AgentTechnology).where(AgentTechnology.slug == spec["slug"])
        )
        if existing is not None:
            continue
        session.add(
            AgentTechnology(
                slug=spec["slug"],
                name=spec["name"],
                description=spec["description"],
                platform_enabled=True,
            )
        )
    await session.commit()
    logger.info("bootstrap_agent_technologies_done", slugs=[t["slug"] for t in BUILTIN_TECHNOLOGIES])
