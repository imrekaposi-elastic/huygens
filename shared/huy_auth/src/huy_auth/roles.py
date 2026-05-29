"""Built-in role identifiers and permission map (mirrors services/iam)."""

from __future__ import annotations

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
PERM_SSH_CONNECT = "ssh:connect"
PERM_SSH_SESSION_READ = "ssh:session_read"
PERM_SSH_POLICY_MANAGE = "ssh:policy_manage"

ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    "platform_admin": frozenset(
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
            PERM_SSH_CONNECT,
            PERM_SSH_SESSION_READ,
            PERM_SSH_POLICY_MANAGE,
        }
    ),
    "admin": frozenset(
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
            PERM_SSH_CONNECT,
            PERM_SSH_SESSION_READ,
            PERM_SSH_POLICY_MANAGE,
        }
    ),
    "project_admin": frozenset(
        {
            PERM_ORG_READ,
            PERM_PROJECT_READ,
            PERM_PROJECT_MANAGE,
            PERM_PROJECT_OPERATE,
            PERM_SSH_CONNECT,
            PERM_SSH_SESSION_READ,
            PERM_SSH_POLICY_MANAGE,
        }
    ),
    "operator": frozenset(
        {
            PERM_ORG_READ,
            PERM_PROJECT_READ,
            PERM_PROJECT_OPERATE,
        }
    ),
    "resource_manager": frozenset(
        {
            PERM_ORG_READ,
            PERM_PROJECT_READ,
            PERM_PROJECT_OPERATE,
        }
    ),
    "compliance_admin": frozenset(
        {
            PERM_ORG_READ,
            PERM_INVENTORY_READ,
            PERM_COMPLIANCE_READ,
            PERM_COMPLIANCE_CATALOG_MANAGE,
        }
    ),
    "compliance_engineer": frozenset(
        {
            PERM_ORG_READ,
            PERM_INVENTORY_READ,
            PERM_COMPLIANCE_READ,
            PERM_COMPLIANCE_ASSIGN,
        }
    ),
    "auditor": frozenset(
        {PERM_ORG_READ, PERM_INVENTORY_READ, PERM_COMPLIANCE_READ, PERM_SSH_SESSION_READ}
    ),
    "compliance_reader": frozenset(
        {PERM_ORG_READ, PERM_INVENTORY_READ, PERM_COMPLIANCE_READ}
    ),
    "ssh_access": frozenset({PERM_ORG_READ, PERM_PROJECT_READ, PERM_SSH_CONNECT}),
    "security_engineer": frozenset(
        {
            PERM_ORG_READ,
            PERM_PROJECT_READ,
            PERM_SSH_CONNECT,
            PERM_SSH_POLICY_MANAGE,
        }
    ),
}
