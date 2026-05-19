"""Map domain models to API responses."""

from __future__ import annotations

from huy_iam.auth_context import AuthContext
from huy_iam.models import User
from huy_iam.schemas import OrgMembershipOut, ProjectRoleOut, UserOut


def user_to_out(ctx: AuthContext, db_user: User) -> UserOut:
    return UserOut(
        id=ctx.user_id,
        email=ctx.email,
        username=ctx.username,
        display_name=db_user.display_name,
        is_active=db_user.is_active,
        platform_roles=ctx.platform_roles,
        org_memberships=[
            OrgMembershipOut(organization_id=m.organization_id, roles=m.roles)
            for m in ctx.org_memberships
        ],
        project_roles=[
            ProjectRoleOut(
                organization_id=g.organization_id,
                project_id=g.project_id,
                role=g.role,
            )
            for g in ctx.project_roles
        ],
    )
