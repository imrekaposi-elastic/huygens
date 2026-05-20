from fastapi import APIRouter, HTTPException

from huy_inventory.api.deps import CurrentUserDep, InventoryReadDep, SessionDep, SettingsDep
from huy_inventory.config import Settings
from huy_inventory.schemas import AgentInventorySummary, OrganizationDashboard, SnapshotOut
from huy_inventory.services.projects_client import ProjectsClient, assignments_by_resource
from huy_inventory.services.registry_client import RegistryClient
from huy_inventory.services.snapshot_service import (
    get_snapshot,
    list_snapshots,
    organization_dashboard,
    snapshot_to_out,
    snapshot_to_summary,
)


async def _registry_agents_for_org(
    settings: Settings, organization_id: str
) -> tuple[set[str], dict[str, dict]]:
    targets = await RegistryClient(settings).fetch_poll_targets()
    by_id: dict[str, dict] = {}
    for t in targets:
        if t["organization_id"] != organization_id:
            continue
        by_id[t["agent_id"]] = {
            "name": t.get("name"),
            "connection_status": t.get("connection_status"),
        }
    return set(by_id), by_id

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
    settings: SettingsDep,
) -> OrganizationDashboard:
    if not user.is_platform_admin() and not user.can_access_org(organization_id):
        raise HTTPException(status_code=403, detail="Access denied")
    active_ids, registry_by_id = await _registry_agents_for_org(settings, organization_id)
    try:
        assignment_rows = await ProjectsClient(settings).fetch_resource_assignments(organization_id)
        assignments = assignments_by_resource(assignment_rows)
    except Exception:
        assignments = {}
    return await organization_dashboard(
        session,
        organization_id,
        active_agent_ids=active_ids,
        registry_by_id=registry_by_id,
        assignments=assignments,
    )
