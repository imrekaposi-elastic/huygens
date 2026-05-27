"""Project-scoped authorization helpers."""

from __future__ import annotations

from fastapi import HTTPException

from huy_auth.auth_context import AuthContext
from huy_auth.roles import PERM_PROJECT_MANAGE
from huy_projects.models import Project


def require_project_read(user: AuthContext, project: Project) -> None:
    if not user.can_read_project(project.organization_id, project.id):
        raise HTTPException(status_code=403, detail="Project read access denied")


def require_project_operate(user: AuthContext, project: Project) -> None:
    require_project_read(user, project)
    if not user.can_operate_project(project.organization_id, project.id):
        raise HTTPException(status_code=403, detail="Project operate access denied")


def require_project_manage(user: AuthContext, project: Project) -> None:
    if user.is_platform_admin():
        return
    if user.has_permission(PERM_PROJECT_MANAGE, project.organization_id):
        if "admin" in user.org_roles(project.organization_id):
            return
    if user.can_manage_project(project.organization_id, project.id):
        return
    raise HTTPException(status_code=403, detail="Project manage access denied")


def require_org_ipam_manage(user: AuthContext, organization_id: str) -> None:
    """Create IP pools and run wizard (org admin or platform_admin)."""
    if user.is_platform_admin():
        return
    if "admin" in user.org_roles(organization_id):
        return
    raise HTTPException(status_code=403, detail="Org admin required for IPAM pool management")


def require_link_manage(user: AuthContext, organization_id: str, left: Project, right: Project) -> None:
    """Create/delete links: org admin, platform_admin, or operator on both projects."""
    if user.is_platform_admin():
        return
    if "admin" in user.org_roles(organization_id):
        return
    if user.can_operate_project(organization_id, left.id) and user.can_operate_project(
        organization_id, right.id
    ):
        return
    raise HTTPException(status_code=403, detail="Link management requires operate on both projects")


def require_topology_read(user: AuthContext, organization_id: str) -> None:
    if user.is_platform_admin():
        return
    if not user.can_access_org(organization_id):
        raise HTTPException(status_code=403, detail="Organization access denied")


def require_project_create(user: AuthContext, organization_id: str) -> None:
    if user.is_platform_admin():
        return
    if "admin" in user.org_roles(organization_id):
        return
    if user.has_permission(PERM_PROJECT_MANAGE, organization_id):
        return
    raise HTTPException(status_code=403, detail="Cannot create projects in organization")
