"""Phase 1 registry API tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt
import pytest
from httpx import AsyncClient


def _platform_token() -> str:
    now = datetime.now(UTC)
    claims = {
        "sub": "pa-user",
        "email": "pa@example.com",
        "username": "platform-admin",
        "platform_roles": ["platform_admin"],
        "org_memberships": [],
        "project_roles": [],
        "iss": "huy-iam",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=1)).timestamp()),
    }
    return jwt.encode(claims, "test-jwt-secret-key-minimum-32-bytes!", algorithm="HS256")


def _org_admin_token(org_id: str) -> str:
    now = datetime.now(UTC)
    claims = {
        "sub": "org-admin",
        "email": "admin@example.com",
        "username": "org-admin",
        "platform_roles": [],
        "org_memberships": [{"organization_id": org_id, "roles": ["admin"]}],
        "project_roles": [],
        "iss": "huy-iam",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=1)).timestamp()),
    }
    return jwt.encode(claims, "test-jwt-secret-key-minimum-32-bytes!", algorithm="HS256")


@pytest.mark.asyncio
async def test_register_agent_and_export_token_once(client: AsyncClient) -> None:
    token = _platform_token()
    headers = {"Authorization": f"Bearer {token}"}

    provider = await client.post(
        "/api/v1/providers",
        headers=headers,
        json={"name": "On-prem", "slug": "onprem"},
    )
    assert provider.status_code == 201
    provider_id = provider.json()["id"]

    region = await client.post(
        f"/api/v1/providers/{provider_id}/regions",
        headers=headers,
        json={"name": "Amsterdam", "slug": "ams"},
    )
    assert region.status_code == 201
    region_id = region.json()["id"]

    org_id = "11111111-1111-1111-1111-111111111111"
    agent = await client.post(
        "/api/v1/agents",
        headers=headers,
        json={
            "name": "dommel",
            "base_url": "https://dommel.example:8765",
            "organization_id": org_id,
            "provider_id": provider_id,
            "region_id": region_id,
            "tls_verify": False,
        },
    )
    assert agent.status_code == 201, agent.text
    body = agent.json()
    assert body["agent_token"]
    assert body["token_exported"] is False
    agent_id = body["id"]

    export = await client.post(f"/api/v1/agents/{agent_id}/export-token", headers=headers)
    assert export.status_code == 200
    assert export.json()["agent_token"]

    export2 = await client.post(f"/api/v1/agents/{agent_id}/export-token", headers=headers)
    assert export2.status_code == 409

    listed = await client.get("/api/v1/agents", headers=headers)
    assert listed.status_code == 200
    assert any(a["name"] == "dommel" for a in listed.json())


@pytest.mark.asyncio
async def test_org_admin_can_list_agents_not_register(client: AsyncClient) -> None:
    org_id = "22222222-2222-2222-2222-222222222222"
    pa = {"Authorization": f"Bearer {_platform_token()}"}
    provider = await client.post("/api/v1/providers", headers=pa, json={"name": "P", "slug": "p2"})
    provider_id = provider.json()["id"]
    region = await client.post(
        f"/api/v1/providers/{provider_id}/regions",
        headers=pa,
        json={"name": "R", "slug": "r2"},
    )
    region_id = region.json()["id"]
    await client.post(
        "/api/v1/agents",
        headers=pa,
        json={
            "name": "agent-a",
            "base_url": "https://a.example",
            "organization_id": org_id,
            "provider_id": provider_id,
            "region_id": region_id,
        },
    )

    oa = {"Authorization": f"Bearer {_org_admin_token(org_id)}"}
    forbidden = await client.post(
        "/api/v1/agents",
        headers=oa,
        json={
            "name": "agent-b",
            "base_url": "https://b.example",
            "organization_id": org_id,
            "provider_id": provider_id,
            "region_id": region_id,
        },
    )
    assert forbidden.status_code == 403

    listed = await client.get("/api/v1/agents", headers=oa)
    assert listed.status_code == 200
    assert len(listed.json()) == 1


@pytest.mark.asyncio
async def test_internal_poll_targets(client: AsyncClient, service_headers: dict[str, str]) -> None:
    pa = {"Authorization": f"Bearer {_platform_token()}"}
    provider = await client.post("/api/v1/providers", headers=pa, json={"name": "P", "slug": "p3"})
    provider_id = provider.json()["id"]
    region = await client.post(
        f"/api/v1/providers/{provider_id}/regions",
        headers=pa,
        json={"name": "R", "slug": "r3"},
    )
    region_id = region.json()["id"]
    await client.post(
        "/api/v1/agents",
        headers=pa,
        json={
            "name": "poll-me",
            "base_url": "https://poll.example",
            "organization_id": "33333333-3333-3333-3333-333333333333",
            "provider_id": provider_id,
            "region_id": region_id,
        },
    )
    targets = await client.get("/api/v1/internal/poll-targets", headers=service_headers)
    assert targets.status_code == 200
    assert len(targets.json()) >= 1
    assert targets.json()[0]["agent_token"]


@pytest.mark.asyncio
async def test_internal_agent_connect(client: AsyncClient, service_headers: dict[str, str]) -> None:
    pa = {"Authorization": f"Bearer {_platform_token()}"}
    provider = await client.post("/api/v1/providers", headers=pa, json={"name": "P", "slug": "p4"})
    provider_id = provider.json()["id"]
    region = await client.post(
        f"/api/v1/providers/{provider_id}/regions",
        headers=pa,
        json={"name": "R", "slug": "r4"},
    )
    region_id = region.json()["id"]
    agent = await client.post(
        "/api/v1/agents",
        headers=pa,
        json={
            "name": "connect-me",
            "base_url": "https://connect.example",
            "organization_id": "44444444-4444-4444-4444-444444444444",
            "provider_id": provider_id,
            "region_id": region_id,
        },
    )
    agent_id = agent.json()["id"]
    connect = await client.get(
        f"/api/v1/internal/agents/{agent_id}/connect",
        headers=service_headers,
    )
    assert connect.status_code == 200
    body = connect.json()
    assert body["agent_id"] == agent_id
    assert body["agent_token"]
    assert body["base_url"] == "https://connect.example"
