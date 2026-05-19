"""Authorization unit tests."""

from __future__ import annotations

from huy_auth.auth_context import AuthContext, OrgMembership, ProjectRoleGrant
from huy_projects.models import Project
from huy_projects.services.authorization import (
    require_project_create,
    require_project_operate,
)


def _ctx(**kwargs) -> AuthContext:
    return AuthContext(
        user_id="u1",
        email="u@example.com",
        username="u1",
        **kwargs,
    )


def test_platform_admin_can_operate_any_project() -> None:
    user = _ctx(platform_roles=["platform_admin"])
    project = Project(organization_id="org-1", name="P", slug="p")
    project.id = "proj-1"
    require_project_operate(user, project)


def test_operator_project_grant() -> None:
    user = _ctx(
        project_roles=[
            ProjectRoleGrant(
                organization_id="org-1", project_id="proj-1", role="operator"
            )
        ]
    )
    project = Project(organization_id="org-1", name="P", slug="p")
    project.id = "proj-1"
    require_project_operate(user, project)


def test_org_admin_can_create() -> None:
    user = _ctx(org_memberships=[OrgMembership(organization_id="org-1", roles=["admin"])])
    require_project_create(user, "org-1")
