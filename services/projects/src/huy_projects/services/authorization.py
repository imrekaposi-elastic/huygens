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


def require_project_create(user: AuthContext, organization_id: str) -> None:
    if user.is_platform_admin():
        return
    if "admin" in user.org_roles(organization_id):
        return
    if user.has_permission(PERM_PROJECT_MANAGE, organization_id):
        return
    raise HTTPException(status_code=403, detail="Cannot create projects in organization")
