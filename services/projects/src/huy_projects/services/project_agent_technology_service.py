"""Per-project agent technology enablement."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from huy_projects.models import Project, ProjectAgentTechnology
from huy_projects.schemas import ProjectAgentTechnologyOut, ProjectAgentTechnologySet
from huy_projects.services.registry_client import RegistryClient


async def list_for_project(
    session: AsyncSession,
    registry: RegistryClient,
    project: Project,
) -> list[ProjectAgentTechnologyOut]:
    catalog = await registry.fetch_agent_technologies()
    result = await session.execute(
        select(ProjectAgentTechnology).where(ProjectAgentTechnology.project_id == project.id)
    )
    by_tech = {row.agent_technology_id: row for row in result.scalars().all()}
    out: list[ProjectAgentTechnologyOut] = []
    for tech in catalog:
        row = by_tech.get(tech["id"])
        out.append(
            ProjectAgentTechnologyOut(
                agent_technology_id=tech["id"],
                slug=tech["slug"],
                name=tech["name"],
                description=tech.get("description"),
                platform_enabled=tech["platform_enabled"],
                enabled=row.enabled if row is not None else False,
            )
        )
    return out


async def set_for_project(
    session: AsyncSession,
    registry: RegistryClient,
    project: Project,
    body: ProjectAgentTechnologySet,
) -> list[ProjectAgentTechnologyOut]:
    catalog = {t["id"]: t for t in await registry.fetch_agent_technologies()}
    result = await session.execute(
        select(ProjectAgentTechnology).where(ProjectAgentTechnology.project_id == project.id)
    )
    existing = {row.agent_technology_id: row for row in result.scalars().all()}
    for item in body.technologies:
        tech = catalog.get(item.agent_technology_id)
        if tech is None:
            continue
        row = existing.get(item.agent_technology_id)
        if row is None:
            row = ProjectAgentTechnology(
                project_id=project.id,
                agent_technology_id=item.agent_technology_id,
                agent_technology_slug=tech["slug"],
                enabled=item.enabled,
            )
            session.add(row)
        else:
            row.enabled = item.enabled
            row.agent_technology_slug = tech["slug"]
    await session.commit()
    return await list_for_project(session, registry, project)


async def enabled_technology_ids(session: AsyncSession, project_id: str) -> set[str]:
    result = await session.execute(
        select(ProjectAgentTechnology).where(ProjectAgentTechnology.project_id == project_id)
    )
    return {row.agent_technology_id for row in result.scalars().all() if row.enabled}
