"""Internal APIs for inventory (resource ↔ project assignments)."""

from fastapi import APIRouter

from huy_projects.api.deps import SessionDep
from huy_projects.api.deps_internal import InternalServiceDep
from huy_projects.schemas import ResourceAssignmentOut
from huy_projects.services import resource_assignment_service

router = APIRouter(prefix="/api/v1/internal", tags=["internal"])


@router.get(
    "/organizations/{organization_id}/resource-assignments",
    response_model=list[ResourceAssignmentOut],
)
async def list_resource_assignments(
    organization_id: str,
    _service: InternalServiceDep,
    session: SessionDep,
) -> list[ResourceAssignmentOut]:
    return await resource_assignment_service.list_org_resource_assignments(
        session, organization_id
    )
