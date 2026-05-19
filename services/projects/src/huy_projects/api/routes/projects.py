"""Project CRUD and agent listing."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from huy_projects.api.deps import (
    BearerTokenDep,
    CurrentUserDep,
    ReadableProjectDep,
    RegistryClientDep,
    SessionDep,
)
from huy_projects.schemas import AgentSummary, ProjectCreate, ProjectOut, ProjectUpdate
from huy_projects.services import authorization, project_service

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])


@router.post("", response_model=ProjectOut, status_code=201)
async def create_project(
    body: ProjectCreate,
    user: CurrentUserDep,
    session: SessionDep,
) -> ProjectOut:
    authorization.require_project_create(user, body.organization_id)
    if not user.can_access_org(body.organization_id) and not user.is_platform_admin():
        raise HTTPException(status_code=403, detail="Organization access denied")
    project = await project_service.create_project(session, body)
    return project_service.project_to_out(project)


@router.get("", response_model=list[ProjectOut])
async def list_projects(
    user: CurrentUserDep,
    session: SessionDep,
    organization_id: str | None = Query(default=None),
) -> list[ProjectOut]:
    if user.is_platform_admin():
        projects = await project_service.list_projects(session, organization_id=organization_id)
    else:
        if organization_id is not None and not user.can_access_org(organization_id):
            raise HTTPException(status_code=403, detail="Organization access denied")
        projects: list = []
        org_ids = (
            [organization_id]
            if organization_id
            else [m.organization_id for m in user.org_memberships]
        )
        seen: set[str] = set()
        for org_id in org_ids:
            for project in await project_service.list_projects(session, organization_id=org_id):
                if project.id in seen:
                    continue
                if user.can_read_project(project.organization_id, project.id):
                    projects.append(project)
                    seen.add(project.id)
    return [project_service.project_to_out(p) for p in projects]


@router.get("/{project_id}", response_model=ProjectOut)
async def get_project(project: ReadableProjectDep) -> ProjectOut:
    return project_service.project_to_out(project)


@router.patch("/{project_id}", response_model=ProjectOut)
async def update_project(
    body: ProjectUpdate,
    project: ReadableProjectDep,
    user: CurrentUserDep,
    session: SessionDep,
) -> ProjectOut:
    authorization.require_project_manage(user, project)
    updated = await project_service.update_project(session, project, body)
    return project_service.project_to_out(updated)


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project: ReadableProjectDep,
    user: CurrentUserDep,
    session: SessionDep,
) -> None:
    authorization.require_project_manage(user, project)
    await project_service.delete_project(session, project)


@router.get("/{project_id}/agents", response_model=list[AgentSummary])
async def list_project_agents(
    project: ReadableProjectDep,
    registry: RegistryClientDep,
    bearer: BearerTokenDep,
) -> list[AgentSummary]:
    agents = await registry.list_agents(bearer)
    filtered = [a for a in agents if a["organization_id"] == project.organization_id]
    return [
        AgentSummary(
            id=a["id"],
            name=a["name"],
            base_url=a["base_url"],
            organization_id=a["organization_id"],
            connection_status=a["connection_status"],
        )
        for a in filtered
    ]
