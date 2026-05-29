"""SSH session authorization for ssh-gateway."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from huy_iam.auth_context import AuthContext
from huy_iam.roles import PERM_SSH_CONNECT, ProjectRole
from huy_iam.services import ssh_ca_service, ssh_policy_service


@dataclass
class SshAuthorizeResult:
    allowed: bool
    reason: str
    linux_username: str | None = None
    sudoers_lines: list[str] | None = None
    ca_public_key: str | None = None


def _can_ssh_to_project(user: AuthContext, organization_id: str, project_id: str) -> bool:
    if user.is_platform_admin():
        return True
    if user.has_org_role(organization_id, "admin"):
        return True
    if user.has_permission(PERM_SSH_CONNECT, organization_id):
        for grant in user.project_roles:
            if (
                grant.organization_id == organization_id
                and grant.project_id == project_id
                and grant.role
                in {
                    ProjectRole.SSH_ACCESS.value,
                    ProjectRole.PROJECT_ADMIN.value,
                    ProjectRole.SECURITY_ENGINEER.value,
                }
            ):
                return True
        if user.has_org_role(organization_id, "admin"):
            return True
    return False


async def authorize_ssh_session(
    session: AsyncSession,
    settings,
    *,
    user: AuthContext,
    organization_id: str,
    project_id: str,
    vm_name: str,
    vm_assigned_to_project: bool,
) -> SshAuthorizeResult:
    if not vm_assigned_to_project:
        return SshAuthorizeResult(allowed=False, reason="vm_not_in_project")
    if not _can_ssh_to_project(user, organization_id, project_id):
        return SshAuthorizeResult(allowed=False, reason="rbac_denied")
    mapping = await ssh_policy_service.resolve_linux_username(
        session,
        organization_id=organization_id,
        user_id=user.user_id,
        project_id=project_id,
    )
    if mapping is None:
        return SshAuthorizeResult(allowed=False, reason="no_account_mapping")
    ca = await ssh_ca_service.ensure_org_ca(session, settings, organization_id)
    rules = await ssh_policy_service.sudo_rules_for_user(session, organization_id, user.user_id)
    sudoers = ssh_policy_service.sudoers_lines_for_rules(mapping.linux_username, rules)
    return SshAuthorizeResult(
        allowed=True,
        reason="ok",
        linux_username=mapping.linux_username,
        sudoers_lines=sudoers,
        ca_public_key=ca.public_key_openssh,
    )
