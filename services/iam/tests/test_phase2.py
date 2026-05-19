"""Phase 2 Keycloak group mapping and OIDC helpers."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from huy_iam.models import IdpGroupMapping
from huy_iam.services.idp_mapping_service import resolve_roles_from_groups


async def _login(client: AsyncClient, username: str, password: str) -> str:
    r = await client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _mapping(
    org_id: str | None,
    group: str,
    role: str,
    match_type: str = "exact",
) -> IdpGroupMapping:
    return IdpGroupMapping(
        organization_id=org_id,
        idp_group_name=group,
        match_type=match_type,
        huy_role=role,
        priority=0,
        enabled=True,
    )


def test_resolve_roles_union() -> None:
    org_id = "org-1"
    mappings = [
        _mapping(org_id, "acme-admins", "admin"),
        _mapping(org_id, "acme-compliance", "compliance_admin"),
        _mapping(None, "huy-platform-ops", "platform_admin"),
    ]
    platform, org = resolve_roles_from_groups(
        mappings, ["acme-admins", "acme-compliance"], organization_id=org_id
    )
    assert platform == set()
    assert org == {"admin", "compliance_admin"}


def test_resolve_platform_mapping() -> None:
    mappings = [_mapping(None, "huy-platform-ops", "platform_admin")]
    platform, org = resolve_roles_from_groups(
        mappings, ["huy-platform-ops"], organization_id="org-1"
    )
    assert platform == {"platform_admin"}
    assert org == set()


def test_resolve_regex_mapping() -> None:
    org_id = "org-1"
    mappings = [_mapping(org_id, r"acme-.*-operator", "operator", match_type="regex")]
    platform, org = resolve_roles_from_groups(
        mappings, ["acme-prod-operator"], organization_id=org_id
    )
    assert org == {"operator"}


@pytest.mark.asyncio
async def test_org_admin_manages_idp_mappings(client: AsyncClient) -> None:
    pa_token = await _login(client, "platform-admin", "platform-admin-secret-12")
    pa_headers = {"Authorization": f"Bearer {pa_token}"}
    org = await client.post(
        "/api/v1/organizations",
        headers=pa_headers,
        json={"name": "SSO Org", "slug": "sso-org"},
    )
    org_id = org.json()["id"]

    r = await client.post(
        f"/api/v1/organizations/{org_id}/idp-group-mappings",
        headers=pa_headers,
        json={
            "idp_group_name": "acme-admins",
            "match_type": "exact",
            "huy_role": "admin",
        },
    )
    assert r.status_code == 201, r.text
    mapping_id = r.json()["id"]

    listed = await client.get(
        f"/api/v1/organizations/{org_id}/idp-group-mappings",
        headers=pa_headers,
    )
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    patched = await client.patch(
        f"/api/v1/organizations/{org_id}/idp-group-mappings/{mapping_id}",
        headers=pa_headers,
        json={"priority": 10},
    )
    assert patched.status_code == 200
    assert patched.json()["priority"] == 10


@pytest.mark.asyncio
async def test_platform_idp_mapping_requires_platform_admin(client: AsyncClient) -> None:
    pa_token = await _login(client, "platform-admin", "platform-admin-secret-12")
    r = await client.post(
        "/api/v1/platform/idp-group-mappings",
        headers={"Authorization": f"Bearer {pa_token}"},
        json={
            "idp_group_name": "huy-platform-ops",
            "huy_role": "platform_admin",
        },
    )
    assert r.status_code == 201, r.text

    org_token = await _login(client, "platform-admin", "platform-admin-secret-12")
    # platform admin can create org - create org admin and test forbidden
    org = await client.post(
        "/api/v1/organizations",
        headers={"Authorization": f"Bearer {org_token}"},
        json={"name": "X", "slug": "x-org"},
    )
    org_id = org.json()["id"]
    await client.post(
        f"/api/v1/organizations/{org_id}/users",
        headers={"Authorization": f"Bearer {org_token}"},
        json={
            "email": "oa@x.example",
            "username": "x-admin",
            "password": "x-admin-secret-12",
            "org_roles": ["admin"],
        },
    )
    oa_token = await _login(client, "x-admin", "x-admin-secret-12")
    forbidden = await client.post(
        "/api/v1/platform/idp-group-mappings",
        headers={"Authorization": f"Bearer {oa_token}"},
        json={"idp_group_name": "bad", "huy_role": "platform_admin"},
    )
    assert forbidden.status_code == 403


@pytest.mark.asyncio
async def test_oidc_authorize_disabled_by_default(client: AsyncClient) -> None:
    r = await client.get(
        "/api/v1/auth/oidc/authorize",
        params={"organization_id": "00000000-0000-0000-0000-000000000001"},
    )
    assert r.status_code == 503
