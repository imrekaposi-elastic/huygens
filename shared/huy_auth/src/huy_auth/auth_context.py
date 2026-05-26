"""Authenticated principal from IAM JWT claims."""

from __future__ import annotations

from dataclasses import dataclass, field

from huy_auth.roles import PERM_PROJECT_READ, ROLE_PERMISSIONS


@dataclass
class OrgMembership:
    organization_id: str
    roles: list[str] = field(default_factory=list)


@dataclass
class ProjectRoleGrant:
    organization_id: str
    project_id: str
    role: str


@dataclass
class AuthContext:
    user_id: str
    email: str
    username: str
    platform_roles: list[str] = field(default_factory=list)
    org_memberships: list[OrgMembership] = field(default_factory=list)
    project_roles: list[ProjectRoleGrant] = field(default_factory=list)

    def is_platform_admin(self) -> bool:
        return "platform_admin" in self.platform_roles

    def org_roles(self, organization_id: str) -> list[str]:
        for m in self.org_memberships:
            if m.organization_id == organization_id:
                return list(m.roles)
        return []

    def can_access_org(self, organization_id: str) -> bool:
        if self.is_platform_admin():
            return True
        if any(m.organization_id == organization_id for m in self.org_memberships):
            return True
        return any(g.organization_id == organization_id for g in self.project_roles)

    def project_roles_for(self, organization_id: str, project_id: str) -> list[str]:
        return [
            g.role
            for g in self.project_roles
            if g.organization_id == organization_id and g.project_id == project_id
        ]

    def can_operate_project(self, organization_id: str, project_id: str) -> bool:
        if self.is_platform_admin():
            return True
        if "admin" in self.org_roles(organization_id):
            return True
        roles = set(self.project_roles_for(organization_id, project_id))
        return bool(roles & {"project_admin", "operator", "resource_manager"})

    def can_manage_project(self, organization_id: str, project_id: str) -> bool:
        if self.is_platform_admin():
            return True
        if "admin" in self.org_roles(organization_id):
            return True
        return "project_admin" in self.project_roles_for(organization_id, project_id)

    def can_read_project(self, organization_id: str, project_id: str) -> bool:
        if self.is_platform_admin():
            return True
        if self.project_roles_for(organization_id, project_id):
            return True
        if "admin" in self.org_roles(organization_id):
            return True
        # Org-wide read (auditor, compliance_reader, …) requires org membership,
        # not project-only grants — otherwise operator on proj-A could read proj-B.
        if any(m.organization_id == organization_id for m in self.org_memberships):
            if self.has_permission(PERM_PROJECT_READ, organization_id):
                return True
        return False

    def has_permission(self, permission: str, organization_id: str | None = None) -> bool:
        if self.is_platform_admin():
            return permission in ROLE_PERMISSIONS.get("platform_admin", frozenset())
        roles: set[str] = set(self.platform_roles)
        if organization_id:
            roles.update(self.org_roles(organization_id))
            for grant in self.project_roles:
                if grant.organization_id == organization_id:
                    roles.add(grant.role)
        else:
            for m in self.org_memberships:
                roles.update(m.roles)
        for role in roles:
            if permission in ROLE_PERMISSIONS.get(role, frozenset()):
                return True
        return False

    @classmethod
    def from_jwt_claims(cls, claims: dict) -> AuthContext:
        org_memberships = [
            OrgMembership(organization_id=m["organization_id"], roles=list(m.get("roles", [])))
            for m in claims.get("org_memberships", [])
        ]
        project_roles = [
            ProjectRoleGrant(
                organization_id=g["organization_id"],
                project_id=g["project_id"],
                role=g["role"],
            )
            for g in claims.get("project_roles", [])
        ]
        return cls(
            user_id=claims["sub"],
            email=claims.get("email", ""),
            username=claims.get("username", ""),
            platform_roles=list(claims.get("platform_roles", [])),
            org_memberships=org_memberships,
            project_roles=project_roles,
        )
