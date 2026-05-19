"""
RBAC helpers for Huygens services (Phase 1a).

Other control-plane services should validate JWTs issued by IAM using the same
secret and claim shape, or call IAM /api/v1/auth/me for introspection.
"""

from __future__ import annotations

from huy_iam.auth_context import AuthContext
from huy_iam.roles import (
    PERM_AGENT_EXPORT_TOKEN,
    PERM_AGENT_REGISTER,
    PERM_INVENTORY_READ,
    PERM_ORG_MANAGE_USERS,
    PERM_PLATFORM_MANAGE_ORGS,
    ROLE_PERMISSIONS,
)

__all__ = [
    "AuthContext",
    "ROLE_PERMISSIONS",
    "PERM_AGENT_REGISTER",
    "PERM_AGENT_EXPORT_TOKEN",
    "PERM_INVENTORY_READ",
    "PERM_ORG_MANAGE_USERS",
    "PERM_PLATFORM_MANAGE_ORGS",
]
