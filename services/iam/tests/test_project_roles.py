"""Project-scoped RBAC assignments."""

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
async def test_assign_project_role_ensures_org_membership(client: AsyncClient) -> None:
    admin_token = await _login(client, "platform-admin", "platform-admin-secret-12")
    headers = {"Authorization": f"Bearer {admin_token}"}

    r = await client.post(
        "/api/v1/organizations",
        headers=headers,
        json={"name": "Proj Roles Org", "slug": "proj-roles-org"},
    )
    assert r.status_code == 201, r.text
    org_id = r.json()["id"]

    r = await client.post(
        f"/api/v1/organizations/{org_id}/users",
        headers=headers,
        json={
            "email": "operator@proj.example",
            "username": "proj-operator",
            "password": "proj-operator-secret",
            "org_roles": [],
        },
    )
    assert r.status_code == 201, r.text
    user_id = r.json()["id"]

    project_id = "00000000-0000-0000-0000-000000000099"
    r = await client.post(
        f"/api/v1/organizations/{org_id}/users/{user_id}/project-roles",
        headers=headers,
        json={"project_id": project_id, "role": "operator"},
    )
    assert r.status_code == 201, r.text

    r = await client.get(f"/api/v1/organizations/{org_id}/users", headers=headers)
    assert r.status_code == 200
    usernames = {u["username"] for u in r.json()}
    assert "proj-operator" in usernames

    op_token = await _login(client, "proj-operator", "proj-operator-secret")
    r = await client.get("/api/v1/organizations", headers={"Authorization": f"Bearer {op_token}"})
    assert r.status_code == 200
    assert any(o["id"] == org_id for o in r.json())

    r = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {op_token}"},
    )
    assert r.status_code == 200
    body = r.json()
    assert any(
        g["project_id"] == project_id and g["role"] == "operator"
        for g in body["project_roles"]
    )


@pytest.mark.asyncio
async def test_revoke_project_role(client: AsyncClient) -> None:
    admin_token = await _login(client, "platform-admin", "platform-admin-secret-12")
    headers = {"Authorization": f"Bearer {admin_token}"}

    r = await client.post(
        "/api/v1/organizations",
        headers=headers,
        json={"name": "Revoke Org", "slug": "revoke-org"},
    )
    org_id = r.json()["id"]

    r = await client.post(
        f"/api/v1/organizations/{org_id}/users",
        headers=headers,
        json={
            "email": "revoke@example.com",
            "username": "revoke-user",
            "password": "revoke-user-secret",
            "org_roles": [],
        },
    )
    user_id = r.json()["id"]
    project_id = "00000000-0000-0000-0000-000000000088"

    r = await client.post(
        f"/api/v1/organizations/{org_id}/users/{user_id}/project-roles",
        headers=headers,
        json={"project_id": project_id, "role": "auditor"},
    )
    assert r.status_code == 201

    r = await client.delete(
        f"/api/v1/organizations/{org_id}/users/{user_id}/project-roles",
        headers=headers,
        params={"project_id": project_id, "role": "auditor"},
    )
    assert r.status_code == 204, r.text

    r = await client.get(
        f"/api/v1/organizations/{org_id}/users",
        headers=headers,
    )
    user = next(u for u in r.json() if u["id"] == user_id)
    assert not any(
        pr["project_id"] == project_id and pr["role"] == "auditor"
        for pr in user["project_roles"]
    )
