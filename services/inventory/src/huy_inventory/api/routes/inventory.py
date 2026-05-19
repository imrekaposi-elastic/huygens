from fastapi import APIRouter, HTTPException

from huy_inventory.api.deps import CurrentUserDep, InventoryReadDep, SessionDep
from huy_inventory.schemas import AgentInventorySummary, OrganizationDashboard, SnapshotOut
from huy_inventory.services.snapshot_service import (
    get_snapshot,
    list_snapshots,
    organization_dashboard,
    snapshot_to_out,
    snapshot_to_summary,
)

router = APIRouter(prefix="/api/v1/inventory", tags=["inventory"])


@router.get("/agents", response_model=list[AgentInventorySummary])
async def list_agent_inventory(
    _user: InventoryReadDep,
    user: CurrentUserDep,
    session: SessionDep,
) -> list[AgentInventorySummary]:
    if user.is_platform_admin():
        rows = await list_snapshots(session)
    else:
        rows = []
        for m in user.org_memberships:
            rows.extend(await list_snapshots(session, organization_id=m.organization_id))
    return [snapshot_to_summary(r) for r in rows]


@router.get("/agents/{agent_id}", response_model=SnapshotOut)
async def get_agent_inventory(
    agent_id: str,
    _user: InventoryReadDep,
    user: CurrentUserDep,
    session: SessionDep,
) -> SnapshotOut:
    row = await get_snapshot(session, agent_id)
    if row is None:
        raise HTTPException(status_code=404, detail="No inventory snapshot for agent")
    if not user.is_platform_admin() and not user.can_access_org(row.organization_id):
        raise HTTPException(status_code=403, detail="Access denied")
    return snapshot_to_out(row)


@router.get("/organizations/{organization_id}/dashboard", response_model=OrganizationDashboard)
async def org_dashboard(
    organization_id: str,
    _user: InventoryReadDep,
    user: CurrentUserDep,
    session: SessionDep,
) -> OrganizationDashboard:
    if not user.is_platform_admin() and not user.can_access_org(organization_id):
        raise HTTPException(status_code=403, detail="Access denied")
    return await organization_dashboard(session, organization_id)
