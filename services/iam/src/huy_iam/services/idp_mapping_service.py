"""IdP group → Huygens role mapping (Phase 2)."""

from __future__ import annotations

import re
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from huy_iam.auth_context import validate_role_name
from huy_iam.models import IdpGroupMapping, UserIdpGroup
from huy_iam.roles import PlatformRole


def _group_matches(mapping: IdpGroupMapping, group: str) -> bool:
    if mapping.match_type == "regex":
        try:
            return re.fullmatch(mapping.idp_group_name, group) is not None
        except re.error:
            return False
    return mapping.idp_group_name == group


def resolve_roles_from_groups(
    mappings: list[IdpGroupMapping],
    groups: list[str],
    *,
    organization_id: str,
) -> tuple[set[str], set[str]]:
    """Return (platform_roles, org_roles) from IdP groups for the login org."""
    platform_roles: set[str] = set()
    org_roles: set[str] = set()
    for mapping in mappings:
        if not mapping.enabled:
            continue
        if not any(_group_matches(mapping, g) for g in groups):
            continue
        if mapping.organization_id is None:
            platform_roles.add(mapping.huy_role)
        elif mapping.organization_id == organization_id:
            org_roles.add(mapping.huy_role)
    return platform_roles, org_roles


async def list_mappings(
    session: AsyncSession, *, organization_id: str | None
) -> list[IdpGroupMapping]:
    stmt = select(IdpGroupMapping)
    if organization_id is None:
        stmt = stmt.where(IdpGroupMapping.organization_id.is_(None))
    else:
        stmt = stmt.where(IdpGroupMapping.organization_id == organization_id)
    stmt = stmt.order_by(IdpGroupMapping.priority.desc(), IdpGroupMapping.idp_group_name)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def list_all_mappings_for_org_login(
    session: AsyncSession, organization_id: str
) -> list[IdpGroupMapping]:
    result = await session.execute(
        select(IdpGroupMapping).where(
            IdpGroupMapping.enabled.is_(True),
            (IdpGroupMapping.organization_id.is_(None))
            | (IdpGroupMapping.organization_id == organization_id),
        )
    )
    return list(result.scalars().all())


async def get_mapping(session: AsyncSession, mapping_id: str) -> IdpGroupMapping | None:
    return await session.get(IdpGroupMapping, mapping_id)


async def create_mapping(
    session: AsyncSession,
    *,
    organization_id: str | None,
    idp_group_name: str,
    match_type: str,
    huy_role: str,
    priority: int,
    enabled: bool,
    created_by: str | None,
) -> IdpGroupMapping:
    if match_type not in ("exact", "regex"):
        raise HTTPException(status_code=400, detail="match_type must be exact or regex")
    if organization_id is None:
        try:
            validate_role_name("platform", huy_role)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        if huy_role != PlatformRole.PLATFORM_ADMIN.value:
            raise HTTPException(
                status_code=400,
                detail="Platform mappings only support platform_admin",
            )
    else:
        try:
            validate_role_name("org", huy_role)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    row = IdpGroupMapping(
        organization_id=organization_id,
        idp_group_name=idp_group_name,
        match_type=match_type,
        huy_role=huy_role,
        priority=priority,
        enabled=enabled,
        created_by=created_by,
    )
    session.add(row)
    await session.flush()
    return row


async def update_mapping(
    session: AsyncSession,
    row: IdpGroupMapping,
    *,
    idp_group_name: str | None,
    match_type: str | None,
    huy_role: str | None,
    priority: int | None,
    enabled: bool | None,
) -> IdpGroupMapping:
    if match_type is not None and match_type not in ("exact", "regex"):
        raise HTTPException(status_code=400, detail="match_type must be exact or regex")
    if idp_group_name is not None:
        row.idp_group_name = idp_group_name
    if match_type is not None:
        row.match_type = match_type
    if huy_role is not None:
        try:
            if row.organization_id is None:
                validate_role_name("platform", huy_role)
            else:
                validate_role_name("org", huy_role)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        row.huy_role = huy_role
    if priority is not None:
        row.priority = priority
    if enabled is not None:
        row.enabled = enabled
    await session.flush()
    return row


async def delete_mapping(session: AsyncSession, row: IdpGroupMapping) -> None:
    await session.delete(row)


async def record_user_idp_groups(
    session: AsyncSession, user_id: str, groups: list[str]
) -> None:
    await session.execute(delete(UserIdpGroup).where(UserIdpGroup.user_id == user_id))
    now = datetime.now(UTC)
    for name in sorted(set(groups)):
        session.add(UserIdpGroup(user_id=user_id, group_name=name, seen_at=now))


async def list_user_idp_groups(session: AsyncSession, user_id: str) -> list[str]:
    result = await session.execute(
        select(UserIdpGroup.group_name)
        .where(UserIdpGroup.user_id == user_id)
        .order_by(UserIdpGroup.group_name)
    )
    return list(result.scalars().all())
