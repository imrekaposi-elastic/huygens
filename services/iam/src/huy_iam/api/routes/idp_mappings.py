"""IdP group → role mapping administration."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from huy_iam.api.deps import CurrentUserDep, PlatformAdminDep, SessionDep
from huy_iam.roles import PERM_ORG_MANAGE_USERS
from huy_iam.schemas import (
    IdpGroupMappingCreate,
    IdpGroupMappingOut,
    IdpGroupMappingUpdate,
    IdpGroupsOut,
)
from huy_iam.services import audit, idp_mapping_service, user_service

org_router = APIRouter(prefix="/api/v1/organizations", tags=["idp-mappings"])
platform_router = APIRouter(prefix="/api/v1/platform/idp-group-mappings", tags=["idp-mappings"])
auth_router = APIRouter(prefix="/api/v1/auth", tags=["auth-oidc"])


@org_router.get("/{organization_id}/idp-group-mappings", response_model=list[IdpGroupMappingOut])
async def list_org_mappings(
    organization_id: str,
    user: CurrentUserDep,
    session: SessionDep,
) -> list[IdpGroupMappingOut]:
    if not user.has_permission(PERM_ORG_MANAGE_USERS, organization_id):
        raise HTTPException(status_code=403, detail="Access denied")
    rows = await idp_mapping_service.list_mappings(session, organization_id=organization_id)
    return [IdpGroupMappingOut.model_validate(r) for r in rows]


@org_router.post(
    "/{organization_id}/idp-group-mappings",
    response_model=IdpGroupMappingOut,
    status_code=201,
)
async def create_org_mapping(
    organization_id: str,
    body: IdpGroupMappingCreate,
    user: CurrentUserDep,
    session: SessionDep,
) -> IdpGroupMappingOut:
    if not user.has_permission(PERM_ORG_MANAGE_USERS, organization_id):
        raise HTTPException(status_code=403, detail="Access denied")
    org = await user_service.get_organization(session, organization_id)
    if org is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    row = await idp_mapping_service.create_mapping(
        session,
        organization_id=organization_id,
        idp_group_name=body.idp_group_name,
        match_type=body.match_type,
        huy_role=body.huy_role,
        priority=body.priority,
        enabled=body.enabled,
        created_by=user.user_id,
    )
    await session.commit()
    await session.refresh(row)
    await audit.record_audit(
        organization_id=organization_id,
        actor_user_id=user.user_id,
        action="idp_mapping.create",
        resource_type="idp_group_mapping",
        resource_id=row.id,
        message=body.idp_group_name,
    )
    return IdpGroupMappingOut.model_validate(row)


@org_router.patch(
    "/{organization_id}/idp-group-mappings/{mapping_id}",
    response_model=IdpGroupMappingOut,
)
async def patch_org_mapping(
    organization_id: str,
    mapping_id: str,
    body: IdpGroupMappingUpdate,
    user: CurrentUserDep,
    session: SessionDep,
) -> IdpGroupMappingOut:
    if not user.has_permission(PERM_ORG_MANAGE_USERS, organization_id):
        raise HTTPException(status_code=403, detail="Access denied")
    row = await idp_mapping_service.get_mapping(session, mapping_id)
    if row is None or row.organization_id != organization_id:
        raise HTTPException(status_code=404, detail="Mapping not found")
    updated = await idp_mapping_service.update_mapping(
        session,
        row,
        idp_group_name=body.idp_group_name,
        match_type=body.match_type,
        huy_role=body.huy_role,
        priority=body.priority,
        enabled=body.enabled,
    )
    await session.commit()
    await session.refresh(updated)
    return IdpGroupMappingOut.model_validate(updated)


@org_router.delete("/{organization_id}/idp-group-mappings/{mapping_id}", status_code=204)
async def delete_org_mapping(
    organization_id: str,
    mapping_id: str,
    user: CurrentUserDep,
    session: SessionDep,
) -> None:
    if not user.has_permission(PERM_ORG_MANAGE_USERS, organization_id):
        raise HTTPException(status_code=403, detail="Access denied")
    row = await idp_mapping_service.get_mapping(session, mapping_id)
    if row is None or row.organization_id != organization_id:
        raise HTTPException(status_code=404, detail="Mapping not found")
    await idp_mapping_service.delete_mapping(session, row)
    await session.commit()
    await audit.record_audit(
        organization_id=organization_id,
        actor_user_id=user.user_id,
        action="idp_mapping.delete",
        resource_type="idp_group_mapping",
        resource_id=mapping_id,
    )


@platform_router.get("", response_model=list[IdpGroupMappingOut])
async def list_platform_mappings(
    _admin: PlatformAdminDep,
    session: SessionDep,
) -> list[IdpGroupMappingOut]:
    rows = await idp_mapping_service.list_mappings(session, organization_id=None)
    return [IdpGroupMappingOut.model_validate(r) for r in rows]


@platform_router.post("", response_model=IdpGroupMappingOut, status_code=201)
async def create_platform_mapping(
    body: IdpGroupMappingCreate,
    admin: PlatformAdminDep,
    session: SessionDep,
) -> IdpGroupMappingOut:
    row = await idp_mapping_service.create_mapping(
        session,
        organization_id=None,
        idp_group_name=body.idp_group_name,
        match_type=body.match_type,
        huy_role=body.huy_role,
        priority=body.priority,
        enabled=body.enabled,
        created_by=admin.user_id,
    )
    await session.commit()
    await session.refresh(row)
    await audit.record_platform_audit(
        actor_user_id=admin.user_id,
        action="idp_mapping.create",
        resource_type="idp_group_mapping",
        resource_id=row.id,
        message=body.idp_group_name,
    )
    return IdpGroupMappingOut.model_validate(row)


@platform_router.patch("/{mapping_id}", response_model=IdpGroupMappingOut)
async def patch_platform_mapping(
    mapping_id: str,
    body: IdpGroupMappingUpdate,
    _admin: PlatformAdminDep,
    session: SessionDep,
) -> IdpGroupMappingOut:
    row = await idp_mapping_service.get_mapping(session, mapping_id)
    if row is None or row.organization_id is not None:
        raise HTTPException(status_code=404, detail="Mapping not found")
    updated = await idp_mapping_service.update_mapping(
        session,
        row,
        idp_group_name=body.idp_group_name,
        match_type=body.match_type,
        huy_role=body.huy_role,
        priority=body.priority,
        enabled=body.enabled,
    )
    await session.commit()
    await session.refresh(updated)
    return IdpGroupMappingOut.model_validate(updated)


@platform_router.delete("/{mapping_id}", status_code=204)
async def delete_platform_mapping(
    mapping_id: str,
    _admin: PlatformAdminDep,
    session: SessionDep,
) -> None:
    row = await idp_mapping_service.get_mapping(session, mapping_id)
    if row is None or row.organization_id is not None:
        raise HTTPException(status_code=404, detail="Mapping not found")
    await idp_mapping_service.delete_mapping(session, row)
    await session.commit()
    await audit.record_platform_audit(
        actor_user_id=_admin.user_id,
        action="idp_mapping.delete",
        resource_type="idp_group_mapping",
        resource_id=mapping_id,
    )


@auth_router.get("/me/idp-groups", response_model=IdpGroupsOut)
async def my_idp_groups(
    user: CurrentUserDep,
    session: SessionDep,
    organization_id: str | None = Query(default=None),
) -> IdpGroupsOut:
    groups = await idp_mapping_service.list_user_idp_groups(session, user.user_id)
    return IdpGroupsOut(groups=groups, organization_id=organization_id)
