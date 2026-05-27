"""JWT helpers for compliance tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt

SECRET = "test-jwt-secret-key-minimum-32-bytes!"
ISSUER = "huy-iam"
ORG_ID = "11111111-1111-1111-1111-111111111111"


def org_admin_token(org_id: str = ORG_ID) -> str:
    return _encode(
        sub="org-admin",
        org_memberships=[{"organization_id": org_id, "roles": ["admin"]}],
    )


def compliance_engineer_token(org_id: str = ORG_ID) -> str:
    return _encode(
        sub="ce",
        org_memberships=[{"organization_id": org_id, "roles": ["compliance_engineer"]}],
    )


def _encode(*, sub: str, org_memberships: list[dict]) -> str:
    now = datetime.now(UTC)
    claims = {
        "sub": sub,
        "email": f"{sub}@example.com",
        "username": sub,
        "platform_roles": [],
        "org_memberships": org_memberships,
        "project_roles": [],
        "iss": ISSUER,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=1)).timestamp()),
    }
    return jwt.encode(claims, SECRET, algorithm="HS256")
