"""Cross-org user administration (platform_admin)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from huy_iam.api.converters import user_to_out
from huy_iam.api.deps import PlatformAdminDep, SessionDep
from huy_iam.auth_context import validate_role_name
from huy_iam.roles import PlatformRole
from huy_iam.schemas import PlatformRoleAssign, UserOut
from huy_iam.services import user_service

router = APIRouter(prefix="/api/v1/users", tags=["users"])


@router.post("/{user_id}/platform-roles", response_model=UserOut)
async def assign_platform_role_endpoint(
    user_id: str,
    body: PlatformRoleAssign,
    _admin: PlatformAdminDep,
    session: SessionDep,
) -> UserOut:
    try:
        validate_role_name("platform", body.role)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if body.role != PlatformRole.PLATFORM_ADMIN:
        raise HTTPException(status_code=400, detail="Only platform_admin supported in Phase 1a")
    target = await user_service.get_user_by_id(session, user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")
    await user_service.grant_platform_role(session, user_id, body.role)
    await session.commit()
    refreshed = await user_service.get_user_by_id(session, user_id)
    if refreshed is None:
        raise HTTPException(status_code=404, detail="User not found")
    ctx = await user_service.build_auth_context(session, refreshed)
    return user_to_out(ctx, refreshed)
