"""Registry internal API tests."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from test_phase1 import _platform_token


@pytest.mark.asyncio
async def test_internal_agent_technologies(client: AsyncClient, service_headers: dict[str, str]) -> None:
    r = await client.get("/api/v1/internal/agent-technologies", headers=service_headers)
    assert r.status_code == 200
    assert any(t["slug"] == "libvirt-agent" for t in r.json())


@pytest.mark.asyncio
async def test_internal_provider_regions_and_poll_targets(
    client: AsyncClient, service_headers: dict[str, str]
) -> None:
    pa = {"Authorization": f"Bearer {_platform_token()}"}
    provider = await client.post(
        "/api/v1/infrastructure-providers",
        headers=pa,
        json={"name": "InternalCo", "slug": "internalco"},
    )
    provider_id = provider.json()["id"]
    region = await client.post(
        f"/api/v1/infrastructure-providers/{provider_id}/regions",
        headers=pa,
        json={"name": "DC", "slug": "dc"},
    )
    region_id = region.json()["id"]

    regions = await client.get(
        f"/api/v1/internal/infrastructure-providers/{provider_id}/regions",
        headers=service_headers,
    )
    assert regions.status_code == 200
    assert any(r["id"] == region_id for r in regions.json())

    tech = (await client.get("/api/v1/agent-technologies", headers=pa)).json()
    libvirt_id = next(t["id"] for t in tech if t["slug"] == "libvirt-agent")
    agent = await client.post(
        "/api/v1/agents",
        headers=pa,
        json={
            "name": "internal-agent",
            "base_url": "https://internal.example",
            "organization_id": "11111111-1111-1111-1111-111111111111",
            "infrastructure_provider_id": provider_id,
            "region_id": region_id,
            "agent_technology_id": libvirt_id,
        },
    )
    agent_id = agent.json()["id"]

    targets = await client.get("/api/v1/internal/poll-targets", headers=service_headers)
    assert targets.status_code == 200
    assert any(t["agent_id"] == agent_id for t in targets.json())

    connect = await client.get(
        f"/api/v1/internal/agents/{agent_id}/connect",
        headers=service_headers,
    )
    assert connect.status_code == 200
    assert connect.json()["agent_id"] == agent_id

    status = await client.patch(
        f"/api/v1/internal/agents/{agent_id}/poll-status",
        headers=service_headers,
        json={"connection_status": "connected"},
    )
    assert status.status_code == 204


@pytest.mark.asyncio
async def test_agent_get_requires_inventory_permission(client: AsyncClient) -> None:
    pa = {"Authorization": f"Bearer {_platform_token()}"}
    tech = (await client.get("/api/v1/agent-technologies", headers=pa)).json()
    libvirt_id = next(t["id"] for t in tech if t["slug"] == "libvirt-agent")
    provider = await client.post(
        "/api/v1/infrastructure-providers",
        headers=pa,
        json={"name": "PermCo", "slug": "permco"},
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
            "name": "perm-agent",
            "base_url": "https://perm.example",
            "organization_id": "11111111-1111-1111-1111-111111111111",
            "infrastructure_provider_id": provider_id,
            "region_id": region_id,
            "agent_technology_id": libvirt_id,
        },
    )
    agent_id = agent.json()["id"]
    detail = await client.get(f"/api/v1/agents/{agent_id}", headers=pa)
    assert detail.status_code == 200
    assert detail.json()["name"] == "perm-agent"
