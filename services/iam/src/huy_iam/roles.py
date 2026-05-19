"""Built-in role identifiers (FRAMEWORK_PLAN + PHASED_PLAN)."""

from __future__ import annotations

from enum import StrEnum


class PlatformRole(StrEnum):
    PLATFORM_ADMIN = "platform_admin"


class OrgRole(StrEnum):
    ADMIN = "admin"
    COMPLIANCE_ADMIN = "compliance_admin"
    COMPLIANCE_ENGINEER = "compliance_engineer"


class ProjectRole(StrEnum):
    PROJECT_ADMIN = "project_admin"
    COMPLIANCE_READER = "compliance_reader"
    OPERATOR = "operator"
    AUDITOR = "auditor"
    SSH_ACCESS = "ssh_access"
    RESOURCE_MANAGER = "resource_manager"
    SECURITY_ENGINEER = "security_engineer"
    COMPLIANCE_ENGINEER = "compliance_engineer"


PLATFORM_ROLES = frozenset(PlatformRole)
ORG_ROLES = frozenset(OrgRole)
PROJECT_ROLES = frozenset(ProjectRole)

# Permissions used by RBAC checks (expand in later phases).
PERM_ORG_READ = "org:read"
PERM_ORG_MANAGE_USERS = "org:manage_users"
PERM_ORG_MANAGE = "org:manage"
PERM_PLATFORM_MANAGE_ORGS = "platform:manage_orgs"
PERM_PLATFORM_ASSIGN_PLATFORM_ADMIN = "platform:assign_platform_admin"
PERM_AGENT_REGISTER = "agent:register"
PERM_AGENT_EXPORT_TOKEN = "agent:export_token"
PERM_INVENTORY_READ = "inventory:read"

ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    PlatformRole.PLATFORM_ADMIN.value: frozenset(
        {
            PERM_ORG_READ,
            PERM_ORG_MANAGE_USERS,
            PERM_ORG_MANAGE,
            PERM_PLATFORM_MANAGE_ORGS,
            PERM_PLATFORM_ASSIGN_PLATFORM_ADMIN,
            PERM_AGENT_REGISTER,
            PERM_AGENT_EXPORT_TOKEN,
            PERM_INVENTORY_READ,
        }
    ),
    OrgRole.ADMIN.value: frozenset(
        {
            PERM_ORG_READ,
            PERM_ORG_MANAGE_USERS,
            PERM_INVENTORY_READ,
        }
    ),
    OrgRole.COMPLIANCE_ADMIN.value: frozenset({PERM_ORG_READ, PERM_INVENTORY_READ}),
    OrgRole.COMPLIANCE_ENGINEER.value: frozenset({PERM_ORG_READ, PERM_INVENTORY_READ}),
    ProjectRole.PROJECT_ADMIN.value: frozenset({PERM_ORG_READ}),
    ProjectRole.OPERATOR.value: frozenset({PERM_ORG_READ}),
    ProjectRole.AUDITOR.value: frozenset({PERM_ORG_READ, PERM_INVENTORY_READ}),
    ProjectRole.COMPLIANCE_READER.value: frozenset({PERM_ORG_READ, PERM_INVENTORY_READ}),
}
