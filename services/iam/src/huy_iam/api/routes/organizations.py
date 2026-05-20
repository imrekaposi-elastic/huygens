"""Organization management."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select

from huy_iam.api.converters import user_to_out
from huy_iam.api.deps import CurrentUserDep, PlatformAdminDep, SessionDep
from huy_iam.auth_context import validate_role_name
from huy_iam.models import Organization
from huy_iam.roles import PERM_ORG_MANAGE_USERS, OrgRole
from huy_iam.schemas import (
    OrganizationCreate,
    OrganizationOut,
    ProjectRoleAssign,
    UserCreate,
    UserOut,
    UserRolesUpdate,
)
from huy_iam.services import user_service

router = APIRouter(prefix="/api/v1/organizations", tags=["organizations"])


@router.post("", response_model=OrganizationOut, status_code=201)
async def create_organization(
    body: OrganizationCreate,
    _admin: PlatformAdminDep,
    session: SessionDep,
) -> OrganizationOut:
    existing = await session.execute(select(Organization).where(Organization.slug == body.slug))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="Organization slug already exists")
    org = await user_service.create_organization(session, body.name, body.slug)
    await session.commit()
    await session.refresh(org)
    return OrganizationOut.model_validate(org)


@router.get("", response_model=list[OrganizationOut])
async def list_organizations(
    user: CurrentUserDep,
    session: SessionDep,
) -> list[OrganizationOut]:
    orgs = await user_service.list_organizations(session)
    if user.is_platform_admin():
        return [OrganizationOut.model_validate(o) for o in orgs]
    allowed = {m.organization_id for m in user.org_memberships}
    allowed |= {g.organization_id for g in user.project_roles}
    return [OrganizationOut.model_validate(o) for o in orgs if o.id in allowed]


@router.delete("/{organization_id}", status_code=204)
async def delete_organization(
    organization_id: str,
    _admin: PlatformAdminDep,
    session: SessionDep,
) -> None:
    deleted = await user_service.delete_organization(session, organization_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Organization not found")
    await session.commit()


@router.get("/{organization_id}", response_model=OrganizationOut)
async def get_organization(
    organization_id: str,
    user: CurrentUserDep,
    session: SessionDep,
) -> OrganizationOut:
    if not user.can_access_org(organization_id):
        raise HTTPException(status_code=403, detail="Access denied")
    org = await user_service.get_organization(session, organization_id)
    if org is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    return OrganizationOut.model_validate(org)


@router.post("/{organization_id}/users", response_model=UserOut, status_code=201)
async def create_org_user(
    organization_id: str,
    body: UserCreate,
    user: CurrentUserDep,
    session: SessionDep,
) -> UserOut:
    if not user.has_permission(PERM_ORG_MANAGE_USERS, organization_id):
        raise HTTPException(status_code=403, detail="Cannot manage users in this organization")
    org = await user_service.get_organization(session, organization_id)
    if org is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    if await user_service.get_user_by_email(session, body.email):
        raise HTTPException(status_code=409, detail="Email already registered")
    if await user_service.get_user_by_username(session, body.username):
        raise HTTPException(status_code=409, detail="Username already taken")
    for role in body.org_roles:
        try:
            validate_role_name("org", role)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    new_user = await user_service.create_user(
        session,
        email=body.email,
        username=body.username,
        password=body.password,
        display_name=body.display_name,
    )
    member = await user_service.ensure_org_member(session, new_user.id, organization_id)
    if body.org_roles:
        await user_service.set_org_roles(session, member, body.org_roles)
    elif not user.is_platform_admin():
        await user_service.set_org_roles(session, member, [OrgRole.ADMIN])
    await session.commit()
    ctx = await user_service.build_auth_context(session, new_user)
    return user_to_out(ctx, new_user)


@router.get("/{organization_id}/users", response_model=list[UserOut])
async def list_org_users(
    organization_id: str,
    user: CurrentUserDep,
    session: SessionDep,
) -> list[UserOut]:
    if not user.can_access_org(organization_id):
        raise HTTPException(status_code=403, detail="Access denied")
    users = await user_service.list_org_users(session, organization_id)
    out: list[UserOut] = []
    for db_user in users:
        ctx = await user_service.build_auth_context(session, db_user)
        out.append(user_to_out(ctx, db_user))
    return out


@router.put("/{organization_id}/users/{user_id}/roles", response_model=UserOut)
async def update_org_user_roles(
    organization_id: str,
    user_id: str,
    body: UserRolesUpdate,
    actor: CurrentUserDep,
    session: SessionDep,
) -> UserOut:
    if not actor.has_permission(PERM_ORG_MANAGE_USERS, organization_id):
        raise HTTPException(status_code=403, detail="Cannot manage users in this organization")
    target = await user_service.get_user_by_id(session, user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")
    for role in body.org_roles:
        try:
            validate_role_name("org", role)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    member = await user_service.ensure_org_member(session, user_id, organization_id)
    await user_service.set_org_roles(session, member, body.org_roles)
    await session.commit()
    ctx = await user_service.build_auth_context(session, target)
    return user_to_out(ctx, target)


@router.delete("/{organization_id}/users/{user_id}", status_code=204)
async def delete_org_user(
    organization_id: str,
    user_id: str,
    actor: CurrentUserDep,
    session: SessionDep,
) -> None:
    if not actor.has_permission(PERM_ORG_MANAGE_USERS, organization_id):
        raise HTTPException(status_code=403, detail="Cannot manage users in this organization")
    if actor.user_id == user_id:
        raise HTTPException(status_code=400, detail="Cannot delete your own user account")
    target = await user_service.get_user_by_id(session, user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")
    deleted = await user_service.delete_org_user(
        session, organization_id=organization_id, user_id=user_id
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="User not found")
    await session.commit()


@router.post("/{organization_id}/users/{user_id}/project-roles", status_code=201)
async def assign_project_role(
    organization_id: str,
    user_id: str,
    body: ProjectRoleAssign,
    actor: CurrentUserDep,
    session: SessionDep,
) -> dict[str, str]:
    if not actor.has_permission(PERM_ORG_MANAGE_USERS, organization_id):
        raise HTTPException(status_code=403, detail="Access denied")
    try:
        validate_role_name("project", body.role)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    target = await user_service.get_user_by_id(session, user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")
    await user_service.assign_project_role(
        session,
        user_id=user_id,
        organization_id=organization_id,
        project_id=body.project_id,
        role=body.role,
    )
    await session.commit()
    return {"status": "assigned", "project_id": body.project_id, "role": body.role}


@router.delete("/{organization_id}/users/{user_id}/project-roles", status_code=204)
async def revoke_project_role_endpoint(
    organization_id: str,
    user_id: str,
    actor: CurrentUserDep,
    session: SessionDep,
    project_id: str = Query(...),
    role: str = Query(...),
) -> None:
    if not actor.has_permission(PERM_ORG_MANAGE_USERS, organization_id):
        raise HTTPException(status_code=403, detail="Access denied")
    removed = await user_service.revoke_project_role(
        session,
        user_id=user_id,
        organization_id=organization_id,
        project_id=project_id,
        role=role,
    )
    if not removed:
        raise HTTPException(status_code=404, detail="Project role assignment not found")
    await session.commit()
