"""Project CRUD."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from huy_projects.models import Project
from huy_projects.schemas import ProjectCreate, ProjectOut, ProjectUpdate


def project_to_out(project: Project) -> ProjectOut:
    return ProjectOut(
        id=project.id,
        organization_id=project.organization_id,
        name=project.name,
        slug=project.slug,
        description=project.description,
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


async def get_project(session: AsyncSession, project_id: str) -> Project | None:
    return await session.get(Project, project_id)


async def list_projects(
    session: AsyncSession, *, organization_id: str | None = None
) -> list[Project]:
    stmt = select(Project).order_by(Project.name)
    if organization_id is not None:
        stmt = stmt.where(Project.organization_id == organization_id)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def create_project(session: AsyncSession, body: ProjectCreate) -> Project:
    existing = await session.execute(
        select(Project).where(
            Project.organization_id == body.organization_id,
            Project.slug == body.slug,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="Project slug already exists in organization")
    project = Project(
        organization_id=body.organization_id,
        name=body.name,
        slug=body.slug,
        description=body.description,
    )
    session.add(project)
    await session.commit()
    await session.refresh(project)
    return project


async def update_project(session: AsyncSession, project: Project, body: ProjectUpdate) -> Project:
    if body.name is not None:
        project.name = body.name
    if body.description is not None:
        project.description = body.description
    project.updated_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(project)
    return project


async def delete_project(session: AsyncSession, project: Project) -> None:
    await session.delete(project)
    await session.commit()
