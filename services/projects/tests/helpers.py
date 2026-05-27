"""JWT helpers for tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt

SECRET = "test-jwt-secret-key-minimum-32-bytes!"
ISSUER = "huy-iam"
ORG_ID = "11111111-1111-1111-1111-111111111111"


def platform_token() -> str:
    return _encode(
        sub="pa-user",
        platform_roles=["platform_admin"],
        org_memberships=[],
        project_roles=[],
    )


def org_admin_token(org_id: str) -> str:
    return _encode(
        sub="org-admin",
        org_memberships=[{"organization_id": org_id, "roles": ["admin"]}],
    )


def operator_token(org_id: str, project_id: str) -> str:
    return _encode(
        sub="operator",
        org_memberships=[],
        project_roles=[
            {
                "organization_id": org_id,
                "project_id": project_id,
                "role": "operator",
            }
        ],
    )


def auditor_token(org_id: str, project_id: str) -> str:
    return _encode(
        sub="auditor",
        org_memberships=[],
        project_roles=[
            {
                "organization_id": org_id,
                "project_id": project_id,
                "role": "auditor",
            }
        ],
    )


def _encode(
    *,
    sub: str,
    platform_roles: list[str] | None = None,
    org_memberships: list[dict] | None = None,
    project_roles: list[dict] | None = None,
) -> str:
    now = datetime.now(UTC)
    claims = {
        "sub": sub,
        "email": f"{sub}@example.com",
        "username": sub,
        "platform_roles": platform_roles or [],
        "org_memberships": org_memberships or [],
        "project_roles": project_roles or [],
        "iss": ISSUER,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=1)).timestamp()),
    }
    return jwt.encode(claims, SECRET, algorithm="HS256")
