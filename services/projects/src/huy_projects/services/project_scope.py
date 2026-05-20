"""Enforce exclusive project membership for agent-scoped resources."""

from __future__ import annotations

from typing import Any, Literal

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from huy_projects.models import Project, ProjectResource

ScopedResourceType = Literal["vm", "network", "cloud_init"]


async def resource_names_in_project(
    session: AsyncSession,
    *,
    project_id: str,
    agent_id: str,
    resource_type: ScopedResourceType,
) -> set[str]:
    result = await session.execute(
        select(ProjectResource.name).where(
            ProjectResource.project_id == project_id,
            ProjectResource.agent_id == agent_id,
            ProjectResource.resource_type == resource_type,
        )
    )
    return {row[0] for row in result.all()}


async def require_resource_in_project(
    session: AsyncSession,
    project: Project,
    *,
    agent_id: str,
    resource_type: ScopedResourceType,
    name: str,
) -> None:
    names = await resource_names_in_project(
        session,
        project_id=project.id,
        agent_id=agent_id,
        resource_type=resource_type,
    )
    if name not in names:
        raise HTTPException(
            status_code=404,
            detail=f"{resource_type.replace('_', '-')} '{name}' is not part of this project",
        )


def filter_agent_items(
    items: list[dict[str, Any]],
    allowed_names: set[str],
    *,
    name_key: str = "name",
) -> list[dict[str, Any]]:
    if not allowed_names:
        return []
    return [item for item in items if item.get(name_key) in allowed_names]


async def filter_agent_list(
    session: AsyncSession,
    project: Project,
    *,
    agent_id: str,
    resource_type: ScopedResourceType,
    items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    names = await resource_names_in_project(
        session,
        project_id=project.id,
        agent_id=agent_id,
        resource_type=resource_type,
    )
    return filter_agent_items(items, names)
