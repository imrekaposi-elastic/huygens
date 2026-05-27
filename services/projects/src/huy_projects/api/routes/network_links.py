"""Org-scoped network link CRUD and topology (Phase 6)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from huy_projects.api.deps import AgentProxyDep, CurrentUserDep, SessionDep, SettingsDep
from huy_projects.schemas import NetworkLinkCreate, NetworkLinkOut, TopologyOut
from huy_projects.services import authorization, link_service, project_service

router = APIRouter(prefix="/api/v1/organizations/{organization_id}", tags=["network-links"])


def _check_org_access(user, organization_id: str) -> None:
    authorization.require_topology_read(user, organization_id)


@router.get("/network-links", response_model=list[NetworkLinkOut])
async def list_network_links(
    organization_id: str,
    user: CurrentUserDep,
    session: SessionDep,
) -> list[NetworkLinkOut]:
    _check_org_access(user, organization_id)
    links = await link_service.list_links(session, organization_id)
    return [link_service.link_to_out(link) for link in links]


@router.post("/network-links", response_model=NetworkLinkOut, status_code=201)
async def create_network_link(
    organization_id: str,
    body: NetworkLinkCreate,
    user: CurrentUserDep,
    session: SessionDep,
    settings: SettingsDep,
    proxy: AgentProxyDep,
) -> NetworkLinkOut:
    _check_org_access(user, organization_id)
    left_project = await project_service.get_project(session, body.left.project_id)
    right_project = await project_service.get_project(session, body.right.project_id)
    if left_project is None or right_project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    if left_project.organization_id != organization_id or right_project.organization_id != organization_id:
        raise HTTPException(status_code=400, detail="Projects must belong to organization")
    authorization.require_link_manage(user, organization_id, left_project, right_project)
    link = await link_service.create_link(
        session, organization_id, body, settings, proxy=proxy
    )
    return link_service.link_to_out(link)


@router.get("/network-links/{link_id}", response_model=NetworkLinkOut)
async def get_network_link(
    organization_id: str,
    link_id: str,
    user: CurrentUserDep,
    session: SessionDep,
) -> NetworkLinkOut:
    _check_org_access(user, organization_id)
    link = await link_service.get_link(session, organization_id, link_id)
    if link is None:
        raise HTTPException(status_code=404, detail="Link not found")
    return link_service.link_to_out(link)


@router.delete("/network-links/{link_id}", status_code=202)
async def delete_network_link(
    organization_id: str,
    link_id: str,
    user: CurrentUserDep,
    session: SessionDep,
) -> NetworkLinkOut:
    _check_org_access(user, organization_id)
    link = await link_service.get_link(session, organization_id, link_id)
    if link is None:
        raise HTTPException(status_code=404, detail="Link not found")
    left_project = await project_service.get_project(session, link.left_project_id)
    right_project = await project_service.get_project(session, link.right_project_id)
    if left_project is None or right_project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    authorization.require_link_manage(user, organization_id, left_project, right_project)
    link = await link_service.delete_link(session, link)
    return link_service.link_to_out(link)


@router.get("/topology", response_model=TopologyOut)
async def get_topology(
    organization_id: str,
    user: CurrentUserDep,
    session: SessionDep,
) -> TopologyOut:
    _check_org_access(user, organization_id)
    return await link_service.build_topology(session, organization_id)
