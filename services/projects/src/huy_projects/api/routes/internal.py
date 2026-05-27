"""Internal APIs for inventory (resource ↔ project assignments)."""

from fastapi import APIRouter

from huy_projects.api.deps import SessionDep
from huy_projects.api.deps_internal import InternalServiceDep
from huy_projects.schemas import ProjectOut, ResourceAssignmentOut
from huy_projects.services import project_service, resource_assignment_service

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


@router.get(
    "/organizations/{organization_id}/projects",
    response_model=list[ProjectOut],
)
async def list_organization_projects(
    organization_id: str,
    _service: InternalServiceDep,
    session: SessionDep,
) -> list[ProjectOut]:
    projects = await project_service.list_projects(session, organization_id=organization_id)
    return [project_service.project_to_out(p) for p in projects]
