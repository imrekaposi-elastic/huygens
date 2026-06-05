"""Additional project authorization coverage."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from huy_auth.auth_context import AuthContext, OrgMembership, ProjectRoleGrant
from huy_projects.models import Project
from huy_projects.services.authorization import (
    require_link_manage,
    require_org_ipam_manage,
    require_project_manage,
    require_project_read,
    require_ssh_trust_setup,
    require_topology_read,
)


def _project() -> Project:
    p = Project(organization_id="org-1", name="Demo", slug="demo")
    p.id = "proj-1"
    return p


def test_org_ipam_manage_denied_for_operator() -> None:
    user = AuthContext(
        user_id="u1",
        email="u@example.com",
        username="u1",
        project_roles=[
            ProjectRoleGrant(organization_id="org-1", project_id="proj-1", role="operator")
        ],
    )
    with pytest.raises(HTTPException) as exc:
        require_org_ipam_manage(user, "org-1")
    assert exc.value.status_code == 403


def test_org_ipam_manage_allowed_for_org_admin() -> None:
    user = AuthContext(
        user_id="u1",
        email="u@example.com",
        username="u1",
        org_memberships=[OrgMembership(organization_id="org-1", roles=["admin"])],
    )
    require_org_ipam_manage(user, "org-1")


def test_link_manage_requires_operate_on_both_projects() -> None:
    user = AuthContext(
        user_id="u1",
        email="u@example.com",
        username="u1",
        project_roles=[
            ProjectRoleGrant(organization_id="org-1", project_id="proj-1", role="operator"),
            ProjectRoleGrant(organization_id="org-1", project_id="proj-2", role="operator"),
        ],
    )
    left = _project()
    right = Project(organization_id="org-1", name="Other", slug="other")
    right.id = "proj-2"
    require_link_manage(user, "org-1", left, right)


def test_topology_read_denied_without_org_access() -> None:
    user = AuthContext(user_id="u1", email="u@example.com", username="u1")
    with pytest.raises(HTTPException) as exc:
        require_topology_read(user, "org-1")
    assert exc.value.status_code == 403


def test_project_manage_via_project_admin() -> None:
    user = AuthContext(
        user_id="u1",
        email="u@example.com",
        username="u1",
        project_roles=[
            ProjectRoleGrant(organization_id="org-1", project_id="proj-1", role="project_admin")
        ],
    )
    require_project_manage(user, _project())


def test_ssh_trust_setup_via_org_admin() -> None:
    user = AuthContext(
        user_id="u1",
        email="u@example.com",
        username="u1",
        org_memberships=[OrgMembership(organization_id="org-1", roles=["admin"])],
    )
    require_ssh_trust_setup(user, _project())


def test_project_read_denied_for_wrong_project() -> None:
    user = AuthContext(
        user_id="u1",
        email="u@example.com",
        username="u1",
        project_roles=[
            ProjectRoleGrant(organization_id="org-1", project_id="proj-2", role="operator")
        ],
    )
    with pytest.raises(HTTPException) as exc:
        require_project_read(user, _project())
    assert exc.value.status_code == 403
