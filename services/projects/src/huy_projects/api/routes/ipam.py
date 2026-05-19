"""IPAM pools, allocations, and subnet wizard (Phase 4)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from sqlalchemy import select

from huy_projects.api.deps import CurrentUserDep, SessionDep
from huy_projects.models import IpAllocation
from huy_projects.schemas import (
    IpAllocationOut,
    IpPoolCreate,
    IpPoolOut,
    WizardApplyRequest,
    WizardPlanRequest,
    WizardPlanResponse,
)
from huy_projects.services import authorization, ipam_service, project_service

router = APIRouter(prefix="/api/v1/organizations/{organization_id}/ipam", tags=["ipam"])


def _check_org_access(user, organization_id: str) -> None:
    if not user.is_platform_admin() and not user.can_access_org(organization_id):
        raise HTTPException(status_code=403, detail="Organization access denied")


@router.post("/pools", response_model=IpPoolOut, status_code=201)
async def create_pool(
    organization_id: str,
    body: IpPoolCreate,
    user: CurrentUserDep,
    session: SessionDep,
) -> IpPoolOut:
    _check_org_access(user, organization_id)
    authorization.require_org_ipam_manage(user, organization_id)
    pool = await ipam_service.create_pool(session, organization_id, body)
    return ipam_service.pool_to_out(pool)


@router.get("/pools", response_model=list[IpPoolOut])
async def list_pools(
    organization_id: str,
    user: CurrentUserDep,
    session: SessionDep,
) -> list[IpPoolOut]:
    _check_org_access(user, organization_id)
    pools = await ipam_service.list_pools(session, organization_id)
    return [ipam_service.pool_to_out(p) for p in pools]


@router.get("/pools/{pool_id}/allocations", response_model=list[IpAllocationOut])
async def list_pool_allocations(
    organization_id: str,
    pool_id: str,
    user: CurrentUserDep,
    session: SessionDep,
) -> list[IpAllocationOut]:
    _check_org_access(user, organization_id)
    pool = await ipam_service.get_pool(session, pool_id)
    if pool is None or pool.organization_id != organization_id:
        raise HTTPException(status_code=404, detail="Pool not found")
    result = await session.execute(select(IpAllocation).where(IpAllocation.pool_id == pool_id))
    return [ipam_service.allocation_to_out(r) for r in result.scalars().all()]


@router.post("/wizard/plan", response_model=WizardPlanResponse)
async def wizard_plan(
    organization_id: str,
    body: WizardPlanRequest,
    user: CurrentUserDep,
    session: SessionDep,
) -> WizardPlanResponse:
    _check_org_access(user, organization_id)
    authorization.require_org_ipam_manage(user, organization_id)
    pool = await ipam_service.get_pool(session, body.pool_id)
    if pool is None or pool.organization_id != organization_id:
        raise HTTPException(status_code=404, detail="Pool not found")
    return await ipam_service.wizard_plan(session, body)


@router.post("/projects/{project_id}/wizard/apply", response_model=list[IpAllocationOut])
async def wizard_apply(
    organization_id: str,
    project_id: str,
    body: WizardApplyRequest,
    user: CurrentUserDep,
    session: SessionDep,
) -> list[IpAllocationOut]:
    project = await project_service.get_project(session, project_id)
    if project is None or project.organization_id != organization_id:
        raise HTTPException(status_code=404, detail="Project not found")
    authorization.require_project_operate(user, project)
    return await ipam_service.wizard_apply(session, project, body)
