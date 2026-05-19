"""Persist desired state for proxied resources."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from huy_projects.models import ProjectResource


async def upsert_desired_state(
    session: AsyncSession,
    *,
    project_id: str,
    agent_id: str,
    resource_type: Literal["vm", "network"],
    name: str,
    desired_state: dict[str, Any] | None,
) -> ProjectResource:
    result = await session.execute(
        select(ProjectResource).where(
            ProjectResource.project_id == project_id,
            ProjectResource.agent_id == agent_id,
            ProjectResource.resource_type == resource_type,
            ProjectResource.name == name,
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        row = ProjectResource(
            project_id=project_id,
            agent_id=agent_id,
            resource_type=resource_type,
            name=name,
            desired_state=desired_state,
        )
        session.add(row)
    else:
        row.desired_state = desired_state
        row.updated_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(row)
    return row


async def clear_desired_state(
    session: AsyncSession,
    *,
    project_id: str,
    agent_id: str,
    resource_type: Literal["vm", "network"],
    name: str,
) -> None:
    result = await session.execute(
        select(ProjectResource).where(
            ProjectResource.project_id == project_id,
            ProjectResource.agent_id == agent_id,
            ProjectResource.resource_type == resource_type,
            ProjectResource.name == name,
        )
    )
    row = result.scalar_one_or_none()
    if row is not None:
        await session.delete(row)
        await session.commit()
