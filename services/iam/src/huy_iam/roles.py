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
PERM_PROJECT_READ = "project:read"
PERM_PROJECT_MANAGE = "project:manage"
PERM_PROJECT_OPERATE = "project:operate"
PERM_COMPLIANCE_READ = "compliance:read"
PERM_COMPLIANCE_CATALOG_MANAGE = "compliance:catalog_manage"
PERM_COMPLIANCE_ASSIGN = "compliance:assign"

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
            PERM_PROJECT_READ,
            PERM_PROJECT_MANAGE,
            PERM_PROJECT_OPERATE,
            PERM_COMPLIANCE_READ,
            PERM_COMPLIANCE_CATALOG_MANAGE,
            PERM_COMPLIANCE_ASSIGN,
        }
    ),
    OrgRole.ADMIN.value: frozenset(
        {
            PERM_ORG_READ,
            PERM_ORG_MANAGE_USERS,
            PERM_INVENTORY_READ,
            PERM_PROJECT_READ,
            PERM_PROJECT_MANAGE,
            PERM_PROJECT_OPERATE,
            PERM_COMPLIANCE_READ,
            PERM_COMPLIANCE_CATALOG_MANAGE,
            PERM_COMPLIANCE_ASSIGN,
        }
    ),
    OrgRole.COMPLIANCE_ADMIN.value: frozenset(
        {
            PERM_ORG_READ,
            PERM_INVENTORY_READ,
            PERM_COMPLIANCE_READ,
            PERM_COMPLIANCE_CATALOG_MANAGE,
        }
    ),
    OrgRole.COMPLIANCE_ENGINEER.value: frozenset(
        {
            PERM_ORG_READ,
            PERM_INVENTORY_READ,
            PERM_COMPLIANCE_READ,
            PERM_COMPLIANCE_ASSIGN,
        }
    ),
    ProjectRole.PROJECT_ADMIN.value: frozenset(
        {
            PERM_ORG_READ,
            PERM_PROJECT_READ,
            PERM_PROJECT_MANAGE,
            PERM_PROJECT_OPERATE,
        }
    ),
    ProjectRole.OPERATOR.value: frozenset(
        {PERM_ORG_READ, PERM_PROJECT_READ, PERM_PROJECT_OPERATE}
    ),
    ProjectRole.RESOURCE_MANAGER.value: frozenset(
        {PERM_ORG_READ, PERM_PROJECT_READ, PERM_PROJECT_OPERATE}
    ),
    ProjectRole.AUDITOR.value: frozenset(
        {PERM_ORG_READ, PERM_INVENTORY_READ, PERM_COMPLIANCE_READ}
    ),
    ProjectRole.COMPLIANCE_READER.value: frozenset(
        {PERM_ORG_READ, PERM_INVENTORY_READ, PERM_COMPLIANCE_READ}
    ),
}
