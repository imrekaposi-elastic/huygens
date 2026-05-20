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


def test_project_only_user_can_access_org_and_read_project() -> None:
    user = _ctx(
        project_roles=[
            ProjectRoleGrant(
                organization_id="org-1", project_id="proj-1", role="operator"
            )
        ]
    )
    assert user.can_access_org("org-1")
    assert user.can_read_project("org-1", "proj-1")
    assert not user.can_read_project("org-1", "proj-2")
