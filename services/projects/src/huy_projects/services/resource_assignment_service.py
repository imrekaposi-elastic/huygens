"""Project membership for agent resources (desired-state catalog)."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from huy_projects.libvirt_system import is_system_network
from huy_projects.models import Project, ProjectResource
from huy_projects.schemas import ResourceAssignmentOut
from huy_projects.services import desired_state
from huy_projects.services.project_scope import ScopedResourceType


async def list_org_resource_assignments(
    session: AsyncSession, organization_id: str
) -> list[ResourceAssignmentOut]:
    stmt = (
        select(
            ProjectResource.agent_id,
            ProjectResource.resource_type,
            ProjectResource.name,
            ProjectResource.project_id,
            Project.name.label("project_name"),
            Project.slug.label("project_slug"),
        )
        .join(Project, Project.id == ProjectResource.project_id)
        .where(Project.organization_id == organization_id)
        .order_by(Project.name, ProjectResource.resource_type, ProjectResource.name)
    )
    result = await session.execute(stmt)
    rows = result.all()
    return [
        ResourceAssignmentOut(
            agent_id=row.agent_id,
            resource_type=row.resource_type,  # type: ignore[arg-type]
            name=row.name,
            project_id=row.project_id,
            project_name=row.project_name,
            project_slug=row.project_slug,
        )
        for row in rows
    ]


async def _assignment_for_resource(
    session: AsyncSession,
    organization_id: str,
    agent_id: str,
    resource_type: str,
    name: str,
) -> tuple[ProjectResource, Project] | None:
    stmt = (
        select(ProjectResource, Project)
        .join(Project, Project.id == ProjectResource.project_id)
        .where(
            Project.organization_id == organization_id,
            ProjectResource.agent_id == agent_id,
            ProjectResource.resource_type == resource_type,
            ProjectResource.name == name,
        )
    )
    result = await session.execute(stmt)
    row = result.first()
    if row is None:
        return None
    return row[0], row[1]


async def assign_resource(
    session: AsyncSession,
    project: Project,
    *,
    agent_id: str,
    resource_type: ScopedResourceType,
    name: str,
    actual_state: dict[str, Any],
) -> ResourceAssignmentOut:
    if resource_type == "network" and is_system_network(name):
        raise HTTPException(
            status_code=400,
            detail=f"Network '{name}' is a system network and cannot be assigned to a project",
        )
    existing = await _assignment_for_resource(
        session, project.organization_id, agent_id, resource_type, name
    )
    if existing is not None:
        row, owner = existing
        if owner.id != project.id:
            raise HTTPException(
                status_code=409,
                detail=f"{resource_type} '{name}' is already assigned to project '{owner.name}'",
            )
    await desired_state.upsert_desired_state(
        session,
        project_id=project.id,
        agent_id=agent_id,
        resource_type=resource_type,
        name=name,
        desired_state=actual_state,
    )
    return ResourceAssignmentOut(
        agent_id=agent_id,
        resource_type=resource_type,
        name=name,
        project_id=project.id,
        project_name=project.name,
        project_slug=project.slug,
    )


async def unassign_resource(
    session: AsyncSession,
    project: Project,
    *,
    agent_id: str,
    resource_type: ScopedResourceType,
    name: str,
) -> None:
    existing = await _assignment_for_resource(
        session, project.organization_id, agent_id, resource_type, name
    )
    if existing is None:
        raise HTTPException(status_code=404, detail="Resource is not assigned to any project")
    row, owner = existing
    if owner.id != project.id:
        raise HTTPException(
            status_code=409,
            detail=f"{resource_type} '{name}' is assigned to project '{owner.name}', not this project",
        )
    await desired_state.clear_desired_state(
        session,
        project_id=project.id,
        agent_id=agent_id,
        resource_type=resource_type,
        name=name,
    )
