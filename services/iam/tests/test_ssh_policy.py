"""Phase 9 SSH RBAC and policy tests."""

from huy_iam.auth_context import AuthContext, OrgMembership, ProjectRoleGrant
from huy_iam.roles import PERM_SSH_CONNECT, PERM_SSH_SESSION_READ, ROLE_PERMISSIONS


def test_ssh_access_role_permissions() -> None:
    perms = ROLE_PERMISSIONS["ssh_access"]
    assert PERM_SSH_CONNECT in perms
    assert PERM_SSH_SESSION_READ not in perms


def test_auditor_can_read_sessions_not_connect() -> None:
    perms = ROLE_PERMISSIONS["auditor"]
    assert PERM_SSH_SESSION_READ in perms
    assert PERM_SSH_CONNECT not in perms


def test_auth_context_ssh_connect_via_project_role() -> None:
    ctx = AuthContext(
        user_id="u1",
        email="u@example.com",
        username="u",
        project_roles=[
            ProjectRoleGrant(organization_id="org1", project_id="p1", role="ssh_access"),
        ],
    )
    assert ctx.has_permission(PERM_SSH_CONNECT, "org1")
