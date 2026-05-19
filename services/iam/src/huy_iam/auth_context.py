"""Authenticated principal built from JWT or API key."""

from __future__ import annotations

from dataclasses import dataclass, field

from huy_iam.roles import ORG_ROLES, PLATFORM_ROLES, PROJECT_ROLES, ROLE_PERMISSIONS


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

    def has_org_role(self, organization_id: str, *roles: str) -> bool:
        current = set(self.org_roles(organization_id))
        return bool(current.intersection(roles))

    def can_access_org(self, organization_id: str) -> bool:
        if self.is_platform_admin():
            return True
        return any(m.organization_id == organization_id for m in self.org_memberships)

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

    def to_jwt_claims(self) -> dict:
        return {
            "sub": self.user_id,
            "email": self.email,
            "username": self.username,
            "platform_roles": self.platform_roles,
            "org_memberships": [
                {"organization_id": m.organization_id, "roles": m.roles} for m in self.org_memberships
            ],
            "project_roles": [
                {
                    "organization_id": g.organization_id,
                    "project_id": g.project_id,
                    "role": g.role,
                }
                for g in self.project_roles
            ],
        }

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


def validate_role_name(scope: str, role: str) -> None:
    if scope == "platform" and role not in {r.value for r in PLATFORM_ROLES}:
        raise ValueError(f"Unknown platform role: {role}")
    if scope == "org" and role not in {r.value for r in ORG_ROLES}:
        raise ValueError(f"Unknown org role: {role}")
    if scope == "project" and role not in {r.value for r in PROJECT_ROLES}:
        raise ValueError(f"Unknown project role: {role}")
