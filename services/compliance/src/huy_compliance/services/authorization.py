"""Org-scoped RBAC for compliance APIs."""

from __future__ import annotations

from fastapi import HTTPException

from huy_auth.auth_context import AuthContext
from huy_auth.roles import (
    PERM_COMPLIANCE_ASSIGN,
    PERM_COMPLIANCE_CATALOG_MANAGE,
    PERM_COMPLIANCE_READ,
)


def require_org_access(user: AuthContext, organization_id: str) -> None:
    if not user.can_access_org(organization_id):
        raise HTTPException(status_code=403, detail="Organization access denied")


def require_compliance_read(user: AuthContext, organization_id: str) -> None:
    require_org_access(user, organization_id)
    if user.is_platform_admin():
        return
    if user.has_permission(PERM_COMPLIANCE_READ, organization_id):
        return
    if "admin" in user.org_roles(organization_id):
        return
    raise HTTPException(status_code=403, detail="Compliance read access denied")


def require_catalog_manage(user: AuthContext, organization_id: str) -> None:
    require_org_access(user, organization_id)
    if user.is_platform_admin():
        return
    if "admin" in user.org_roles(organization_id):
        return
    if user.has_permission(PERM_COMPLIANCE_CATALOG_MANAGE, organization_id):
        return
    raise HTTPException(status_code=403, detail="Compliance catalog manage access denied")


def require_criticality_assign(user: AuthContext, organization_id: str) -> None:
    require_org_access(user, organization_id)
    if user.is_platform_admin():
        return
    if user.has_permission(PERM_COMPLIANCE_ASSIGN, organization_id):
        return
    if "compliance_engineer" in user.org_roles(organization_id):
        return
    raise HTTPException(status_code=403, detail="Compliance engineer role required")
