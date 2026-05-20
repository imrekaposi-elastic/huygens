"""Internal APIs for registry (snapshot cleanup)."""

from fastapi import APIRouter, HTTPException

from huy_inventory.api.deps import SessionDep
from huy_inventory.api.deps_internal import InternalServiceDep
from huy_inventory.services.snapshot_service import delete_snapshot

router = APIRouter(prefix="/api/v1/internal", tags=["internal"])


@router.delete("/snapshots/{agent_id}", status_code=204)
async def remove_agent_snapshot(
    agent_id: str,
    _service: InternalServiceDep,
    session: SessionDep,
) -> None:
    deleted = await delete_snapshot(session, agent_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="No snapshot for agent")
