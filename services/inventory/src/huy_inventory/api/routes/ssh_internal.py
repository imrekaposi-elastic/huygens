"""Internal SSH target resolution for ssh-gateway."""

from fastapi import APIRouter

from huy_inventory.api.deps import SessionDep, SettingsDep
from huy_inventory.api.deps_internal import InternalServiceDep
from huy_inventory.services.ssh_target_service import resolve_ssh_target

router = APIRouter(prefix="/internal/v1/ssh", tags=["ssh-internal"])


@router.get("/target")
async def get_ssh_target(
    organization_id: str,
    project_id: str,
    vm_name: str,
    _service: InternalServiceDep,
    session: SessionDep,
    settings: SettingsDep,
) -> dict:
    return await resolve_ssh_target(
        session,
        settings,
        organization_id=organization_id,
        project_id=project_id,
        vm_name=vm_name,
    )
