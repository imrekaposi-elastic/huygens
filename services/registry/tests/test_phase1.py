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


@pytest.mark.asyncio
async def test_agent_technology_bootstrapped(client: AsyncClient) -> None:
    pa = {"Authorization": f"Bearer {_platform_token()}"}
    r = await client.get("/api/v1/agent-technologies", headers=pa)
    assert r.status_code == 200
    slugs = {row["slug"] for row in r.json()}
    assert "libvirt-agent" in slugs


@pytest.mark.asyncio
async def test_infrastructure_provider_region_tree_and_agent(client: AsyncClient) -> None:
    pa = {"Authorization": f"Bearer {_platform_token()}"}
    tech = (await client.get("/api/v1/agent-technologies", headers=pa)).json()
    libvirt_id = next(t["id"] for t in tech if t["slug"] == "libvirt-agent")

    provider = await client.post(
        "/api/v1/infrastructure-providers",
        headers=pa,
        json={"name": "Hetzner", "slug": "hetzner"},
    )
    assert provider.status_code == 201
    provider_id = provider.json()["id"]

    dc = await client.post(
        f"/api/v1/infrastructure-providers/{provider_id}/regions",
        headers=pa,
        json={"name": "Falkenstein", "slug": "fsn1"},
    )
    assert dc.status_code == 201
    dc_id = dc.json()["id"]

    rack = await client.post(
        f"/api/v1/infrastructure-providers/{provider_id}/regions",
        headers=pa,
        json={"name": "Rack A", "slug": "rack-a", "parent_region_id": dc_id},
    )
    assert rack.status_code == 201
    rack_id = rack.json()["id"]

    tree_before = await client.get(
        f"/api/v1/infrastructure-providers/{provider_id}/region-tree",
        headers=pa,
    )
    assert tree_before.status_code == 200
    assert not tree_before.json()[0]["operational"]

    agent = await client.post(
        "/api/v1/agents",
        headers=pa,
        json={
            "name": "rack-a-agent",
            "base_url": "https://agent.example",
            "organization_id": "11111111-1111-1111-1111-111111111111",
            "infrastructure_provider_id": provider_id,
            "region_id": rack_id,
            "agent_technology_id": libvirt_id,
        },
    )
    assert agent.status_code == 201, agent.text
    assert agent.json()["agent_technology_slug"] == "libvirt-agent"

    detail = await client.get(f"/api/v1/infrastructure-providers/{provider_id}", headers=pa)
    assert detail.status_code == 200
    body = detail.json()
    assert body["operational"] is True
    assert body["total_agents"] == 1
    assert body["region_tree"][0]["operational"] is True
    assert body["region_tree"][0]["children"][0]["operational"] is True


@pytest.mark.asyncio
async def test_migrate_agent_to_parent_region_covers_children(client: AsyncClient) -> None:
    pa = {"Authorization": f"Bearer {_platform_token()}"}
    tech = (await client.get("/api/v1/agent-technologies", headers=pa)).json()
    libvirt_id = next(t["id"] for t in tech if t["slug"] == "libvirt-agent")
    provider = await client.post(
        "/api/v1/infrastructure-providers",
        headers=pa,
        json={"name": "MigrateCo", "slug": "migrateco"},
    )
    provider_id = provider.json()["id"]
    dc = await client.post(
        f"/api/v1/infrastructure-providers/{provider_id}/regions",
        headers=pa,
        json={"name": "DC", "slug": "dc"},
    )
    dc_id = dc.json()["id"]
    rack = await client.post(
        f"/api/v1/infrastructure-providers/{provider_id}/regions",
        headers=pa,
        json={"name": "Rack", "slug": "rack", "parent_region_id": dc_id},
    )
    rack_id = rack.json()["id"]
    agent = await client.post(
        "/api/v1/agents",
        headers=pa,
        json={
            "name": "migrate-me",
            "base_url": "https://migrate.example",
            "organization_id": "55555555-5555-5555-5555-555555555555",
            "infrastructure_provider_id": provider_id,
            "region_id": rack_id,
            "agent_technology_id": libvirt_id,
        },
    )
    agent_id = agent.json()["id"]
    moved = await client.patch(
        f"/api/v1/agents/{agent_id}",
        headers=pa,
        json={"region_id": dc_id, "infrastructure_provider_id": provider_id},
    )
    assert moved.status_code == 200
    assert moved.json()["region_id"] == dc_id
    assert moved.json()["region_name"] == "DC"
    tree = (
        await client.get(f"/api/v1/infrastructure-providers/{provider_id}", headers=pa)
    ).json()
    dc_node = tree["region_tree"][0]
    rack_node = dc_node["children"][0]
    assert dc_node["operational"] is True
    assert dc_node["has_direct_agent"] is True
    assert rack_node["operational"] is True
    assert rack_node["has_direct_agent"] is False


@pytest.mark.asyncio
async def test_delete_region_unassigns_agents_and_subregions(client: AsyncClient) -> None:
    pa = {"Authorization": f"Bearer {_platform_token()}"}
    tech = (await client.get("/api/v1/agent-technologies", headers=pa)).json()
    libvirt_id = next(t["id"] for t in tech if t["slug"] == "libvirt-agent")
    provider = await client.post(
        "/api/v1/infrastructure-providers",
        headers=pa,
        json={"name": "RegDel", "slug": "regdel"},
    )
    provider_id = provider.json()["id"]
    dc = await client.post(
        f"/api/v1/infrastructure-providers/{provider_id}/regions",
        headers=pa,
        json={"name": "DC", "slug": "dc"},
    )
    dc_id = dc.json()["id"]
    rack = await client.post(
        f"/api/v1/infrastructure-providers/{provider_id}/regions",
        headers=pa,
        json={"name": "Rack", "slug": "rack", "parent_region_id": dc_id},
    )
    rack_id = rack.json()["id"]
    agent = await client.post(
        "/api/v1/agents",
        headers=pa,
        json={
            "name": "regdel-agent",
            "base_url": "https://regdel.example",
            "organization_id": "55555555-5555-5555-5555-555555555555",
            "infrastructure_provider_id": provider_id,
            "region_id": rack_id,
            "agent_technology_id": libvirt_id,
        },
    )
    agent_id = agent.json()["id"]
    r = await client.delete(
        f"/api/v1/infrastructure-providers/{provider_id}/regions/{dc_id}",
        headers=pa,
    )
    assert r.status_code == 204
    agent_row = (await client.get(f"/api/v1/agents/{agent_id}", headers=pa)).json()
    assert agent_row["region_id"] is None
    tree = (
        await client.get(f"/api/v1/infrastructure-providers/{provider_id}", headers=pa)
    ).json()
    assert tree["region_tree"] == []


@pytest.mark.asyncio
async def test_platform_admin_deletes_agent(client: AsyncClient) -> None:
    pa = {"Authorization": f"Bearer {_platform_token()}"}
    tech = (await client.get("/api/v1/agent-technologies", headers=pa)).json()
    libvirt_id = next(t["id"] for t in tech if t["slug"] == "libvirt-agent")
    provider = await client.post(
        "/api/v1/infrastructure-providers",
        headers=pa,
        json={"name": "DelCo", "slug": "delco"},
    )
    provider_id = provider.json()["id"]
    region = await client.post(
        f"/api/v1/infrastructure-providers/{provider_id}/regions",
        headers=pa,
        json={"name": "R", "slug": "r"},
    )
    region_id = region.json()["id"]
    agent = await client.post(
        "/api/v1/agents",
        headers=pa,
        json={
            "name": "delete-me",
            "base_url": "https://delete.example",
            "organization_id": "55555555-5555-5555-5555-555555555555",
            "infrastructure_provider_id": provider_id,
            "region_id": region_id,
            "agent_technology_id": libvirt_id,
        },
    )
    agent_id = agent.json()["id"]
    r = await client.delete(f"/api/v1/agents/{agent_id}", headers=pa)
    assert r.status_code == 204
