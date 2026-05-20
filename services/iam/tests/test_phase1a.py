"""Phase 1a IAM integration tests."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


async def _login(client: AsyncClient, username: str, password: str) -> str:
    r = await client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.mark.asyncio
async def test_health(client: AsyncClient) -> None:
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json()["service"] == "huy-iam"


@pytest.mark.asyncio
async def test_bootstrap_login_and_me(client: AsyncClient) -> None:
    token = await _login(client, "platform-admin", "platform-admin-secret-12")
    r = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    body = r.json()
    assert body["username"] == "platform-admin"
    assert "platform_admin" in body["platform_roles"]


@pytest.mark.asyncio
async def test_platform_admin_creates_org_and_org_admin(client: AsyncClient) -> None:
    token = await _login(client, "platform-admin", "platform-admin-secret-12")
    headers = {"Authorization": f"Bearer {token}"}

    r = await client.post(
        "/api/v1/organizations",
        headers=headers,
        json={"name": "Acme Corp", "slug": "acme"},
    )
    assert r.status_code == 201, r.text
    org_id = r.json()["id"]

    r = await client.post(
        f"/api/v1/organizations/{org_id}/users",
        headers=headers,
        json={
            "email": "admin@acme.example",
            "username": "acme-admin",
            "password": "acme-admin-secret",
            "org_roles": ["admin"],
        },
    )
    assert r.status_code == 201, r.text
    assert r.json()["org_memberships"][0]["roles"] == ["admin"]

    org_token = await _login(client, "acme-admin", "acme-admin-secret")
    r = await client.get("/api/v1/organizations", headers={"Authorization": f"Bearer {org_token}"})
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.json()[0]["slug"] == "acme"


@pytest.mark.asyncio
async def test_platform_admin_deletes_organization(client: AsyncClient) -> None:
    token = await _login(client, "platform-admin", "platform-admin-secret-12")
    headers = {"Authorization": f"Bearer {token}"}
    r = await client.post(
        "/api/v1/organizations",
        headers=headers,
        json={"name": "To Delete", "slug": "to-delete"},
    )
    assert r.status_code == 201, r.text
    org_id = r.json()["id"]
    r = await client.delete(f"/api/v1/organizations/{org_id}", headers=headers)
    assert r.status_code == 204, r.text
    r = await client.get("/api/v1/organizations", headers=headers)
    assert all(o["id"] != org_id for o in r.json())


@pytest.mark.asyncio
async def test_org_admin_cannot_create_organization(client: AsyncClient) -> None:
    pa_token = await _login(client, "platform-admin", "platform-admin-secret-12")
    pa_headers = {"Authorization": f"Bearer {pa_token}"}
    r = await client.post(
        "/api/v1/organizations",
        headers=pa_headers,
        json={"name": "Beta", "slug": "beta"},
    )
    org_id = r.json()["id"]
    await client.post(
        f"/api/v1/organizations/{org_id}/users",
        headers=pa_headers,
        json={
            "email": "b@beta.example",
            "username": "beta-admin",
            "password": "beta-admin-secret-12",
            "org_roles": ["admin"],
        },
    )
    token = await _login(client, "beta-admin", "beta-admin-secret-12")
    r = await client.post(
        "/api/v1/organizations",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Gamma", "slug": "gamma"},
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_api_key_login(client: AsyncClient) -> None:
    token = await _login(client, "platform-admin", "platform-admin-secret-12")
    headers = {"Authorization": f"Bearer {token}"}
    r = await client.post("/api/v1/auth/api-keys", headers=headers, json={"name": "ci"})
    assert r.status_code == 201
    api_key = r.json()["api_key"]
    r = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {api_key}"})
    assert r.status_code == 200
    assert r.json()["username"] == "platform-admin"


@pytest.mark.asyncio
async def test_assign_platform_admin(client: AsyncClient) -> None:
    pa_token = await _login(client, "platform-admin", "platform-admin-secret-12")
    pa_headers = {"Authorization": f"Bearer {pa_token}"}
    r = await client.post(
        "/api/v1/organizations",
        headers=pa_headers,
        json={"name": "Delta", "slug": "delta"},
    )
    org_id = r.json()["id"]
    r = await client.post(
        f"/api/v1/organizations/{org_id}/users",
        headers=pa_headers,
        json={
            "email": "ops@delta.example.com",
            "username": "delta-ops",
            "password": "delta-ops-secret-12",
            "org_roles": ["admin"],
        },
    )
    user_id = r.json()["id"]
    r = await client.post(
        f"/api/v1/users/{user_id}/platform-roles",
        headers=pa_headers,
        json={"role": "platform_admin"},
    )
    assert r.status_code == 200
    assert "platform_admin" in r.json()["platform_roles"]
