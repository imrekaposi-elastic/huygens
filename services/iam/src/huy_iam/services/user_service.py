"""User and membership persistence."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from huy_iam.auth_context import AuthContext, OrgMembership, ProjectRoleGrant
from huy_iam.models import (
    ApiKey,
    Organization,
    OrganizationMember,
    OrganizationMemberRole,
    ProjectRoleAssignment,
    User,
    UserPlatformRole,
)
from huy_iam.services import idp_mapping_service
from huy_iam.security import hash_api_key, hash_password


async def get_user_by_username(session: AsyncSession, username: str) -> User | None:
    result = await session.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()


async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    result = await session.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_user_by_id(session: AsyncSession, user_id: str) -> User | None:
    result = await session.execute(
        select(User)
        .where(User.id == user_id)
        .options(
            selectinload(User.platform_roles),
            selectinload(User.org_memberships).selectinload(OrganizationMember.roles),
            selectinload(User.project_roles),
        )
        .execution_options(populate_existing=True)
    )
    return result.scalar_one_or_none()


async def get_user_by_external_subject(
    session: AsyncSession, external_subject: str, realm: str | None
) -> User | None:
    result = await session.execute(
        select(User).where(
            User.external_subject == external_subject,
            User.keycloak_realm == realm,
        )
    )
    return result.scalar_one_or_none()


async def build_auth_context(session: AsyncSession, user: User) -> AuthContext:
    user = await get_user_by_id(session, user.id)
    if user is None:
        raise ValueError("user not found")
    org_memberships: list[OrgMembership] = []
    for member in user.org_memberships:
        org_memberships.append(
            OrgMembership(
                organization_id=member.organization_id,
                roles=[r.role for r in member.roles],
            )
        )
    project_roles = [
        ProjectRoleGrant(
            organization_id=g.organization_id,
            project_id=g.project_id,
            role=g.role,
        )
        for g in user.project_roles
    ]
    return AuthContext(
        user_id=user.id,
        email=user.email,
        username=user.username,
        platform_roles=[r.role for r in user.platform_roles],
        org_memberships=org_memberships,
        project_roles=project_roles,
    )


async def build_auth_context_with_idp(
    session: AsyncSession,
    user: User,
    *,
    organization_id: str,
    idp_groups: list[str],
) -> AuthContext:
    base = await build_auth_context(session, user)
    if not idp_groups:
        return base
    mappings = await idp_mapping_service.list_all_mappings_for_org_login(session, organization_id)
    platform_extra, org_extra = idp_mapping_service.resolve_roles_from_groups(
        mappings, idp_groups, organization_id=organization_id
    )
    platform_roles = sorted(set(base.platform_roles) | platform_extra)
    memberships: dict[str, set[str]] = {
        m.organization_id: set(m.roles) for m in base.org_memberships
    }
    if org_extra:
        memberships.setdefault(organization_id, set()).update(org_extra)
    org_memberships = [
        OrgMembership(organization_id=oid, roles=sorted(roles))
        for oid, roles in memberships.items()
        if roles
    ]
    return AuthContext(
        user_id=base.user_id,
        email=base.email,
        username=base.username,
        platform_roles=platform_roles,
        org_memberships=org_memberships,
        project_roles=base.project_roles,
    )


async def authenticate_password(session: AsyncSession, username: str, password: str) -> User | None:
    from huy_iam.security import verify_password

    user = await get_user_by_username(session, username)
    if user is None or not user.is_active:
        return None
    if user.auth_provider != "local" or not user.password_hash:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


async def authenticate_api_key(session: AsyncSession, full_key: str) -> User | None:
    from datetime import UTC, datetime

    key_hash = hash_api_key(full_key)
    result = await session.execute(
        select(ApiKey)
        .where(ApiKey.key_hash == key_hash)
        .options(selectinload(ApiKey.user))
    )
    api_key = result.scalar_one_or_none()
    if api_key is None or api_key.is_expired():
        return None
    user = api_key.user
    if not user.is_active:
        return None
    api_key.last_used_at = datetime.now(UTC)
    await session.flush()
    return user


async def create_user(
    session: AsyncSession,
    *,
    email: str,
    username: str,
    password: str,
    display_name: str | None = None,
) -> User:
    user = User(
        email=email.lower(),
        username=username,
        password_hash=hash_password(password),
        auth_provider="local",
        display_name=display_name,
    )
    session.add(user)
    await session.flush()
    return user


async def create_oidc_user(
    session: AsyncSession,
    *,
    email: str,
    username: str,
    external_subject: str,
    keycloak_realm: str | None,
    display_name: str | None = None,
) -> User:
    user = User(
        email=email.lower(),
        username=username,
        password_hash=None,
        auth_provider="oidc",
        external_subject=external_subject,
        keycloak_realm=keycloak_realm,
        display_name=display_name,
    )
    session.add(user)
    await session.flush()
    return user


async def grant_platform_role(session: AsyncSession, user_id: str, role: str) -> None:
    existing = await session.execute(
        select(UserPlatformRole).where(
            UserPlatformRole.user_id == user_id,
            UserPlatformRole.role == role,
        )
    )
    if existing.scalar_one_or_none() is not None:
        return
    session.add(UserPlatformRole(user_id=user_id, role=role))


async def ensure_org_member(
    session: AsyncSession, user_id: str, organization_id: str
) -> OrganizationMember:
    result = await session.execute(
        select(OrganizationMember).where(
            OrganizationMember.user_id == user_id,
            OrganizationMember.organization_id == organization_id,
        )
    )
    member = result.scalar_one_or_none()
    if member is not None:
        return member
    member = OrganizationMember(user_id=user_id, organization_id=organization_id)
    session.add(member)
    await session.flush()
    return member


async def set_org_roles(
    session: AsyncSession, member: OrganizationMember, roles: list[str]
) -> None:
    result = await session.execute(
        select(OrganizationMemberRole).where(OrganizationMemberRole.member_id == member.id)
    )
    for row in result.scalars().all():
        await session.delete(row)
    await session.flush()
    for role in sorted(set(roles)):
        session.add(OrganizationMemberRole(member_id=member.id, role=role))


async def create_organization(session: AsyncSession, name: str, slug: str) -> Organization:
    org = Organization(name=name, slug=slug)
    session.add(org)
    await session.flush()
    return org


async def list_organizations(session: AsyncSession) -> list[Organization]:
    result = await session.execute(select(Organization).order_by(Organization.name))
    return list(result.scalars().all())


async def get_organization(session: AsyncSession, org_id: str) -> Organization | None:
    result = await session.execute(select(Organization).where(Organization.id == org_id))
    return result.scalar_one_or_none()


async def delete_organization(session: AsyncSession, org_id: str) -> bool:
    org = await get_organization(session, org_id)
    if org is None:
        return False
    await session.delete(org)
    await session.flush()
    return True


async def list_org_users(session: AsyncSession, organization_id: str) -> list[User]:
    result = await session.execute(
        select(User)
        .join(OrganizationMember)
        .where(OrganizationMember.organization_id == organization_id)
        .options(
            selectinload(User.platform_roles),
            selectinload(User.org_memberships).selectinload(OrganizationMember.roles),
        )
    )
    return list(result.scalars().unique().all())


async def assign_project_role(
    session: AsyncSession,
    *,
    user_id: str,
    organization_id: str,
    project_id: str,
    role: str,
) -> ProjectRoleAssignment:
    grant = ProjectRoleAssignment(
        user_id=user_id,
        organization_id=organization_id,
        project_id=project_id,
        role=role,
    )
    session.add(grant)
    await session.flush()
    return grant
