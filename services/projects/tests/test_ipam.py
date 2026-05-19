"""IPAM API and network create enforcement tests."""

from __future__ import annotations

import os

import pytest
import respx
from httpx import AsyncClient, Response

from helpers import org_admin_token, platform_token

ORG_ID = "11111111-1111-1111-1111-111111111111"


@pytest.mark.asyncio
async def test_create_pool_and_wizard_plan(client: AsyncClient) -> None:
    headers = {"Authorization": f"Bearer {org_admin_token(ORG_ID)}"}
    pool = await client.post(
        f"/api/v1/organizations/{ORG_ID}/ipam/pools",
        headers=headers,
        json={
            "name": "lab-pool",
            "cidr": "10.50.0.0/20",
            "exceptions": ["10.50.0.0/28"],
        },
    )
    assert pool.status_code == 201, pool.text
    pool_id = pool.json()["id"]

    plan = await client.post(
        f"/api/v1/organizations/{ORG_ID}/ipam/wizard/plan",
        headers=headers,
        json={"pool_id": pool_id, "network_count": 2, "hosts_per_network": 20},
    )
    assert plan.status_code == 200
    subnets = plan.json()["subnets"]
    assert len(subnets) == 2
    assert all("cidr" in s for s in subnets)


@pytest.mark.asyncio
async def test_reject_manual_cidr_when_enforced(client: AsyncClient) -> None:
    from huy_projects.config import get_settings

    get_settings.cache_clear()
    os.environ["IPAM_ENFORCE"] = "true"

    headers = {"Authorization": f"Bearer {org_admin_token(ORG_ID)}"}
    project = await client.post(
        "/api/v1/projects",
        headers=headers,
        json={"organization_id": ORG_ID, "name": "IPAM", "slug": "ipam-enforce"},
    )
    project_id = project.json()["id"]
    agent_id = "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee"

    denied = await client.post(
        f"/api/v1/projects/{project_id}/agents/{agent_id}/networks",
        headers=headers,
        json={"name": "lab0", "ipv4_cidr": "192.168.99.0/24"},
    )
    assert denied.status_code == 400
    assert "IPAM" in denied.json()["detail"]

    os.environ["IPAM_ENFORCE"] = "false"
    get_settings.cache_clear()


@pytest.mark.asyncio
@respx.mock
async def test_create_network_with_ipam(client: AsyncClient) -> None:
    headers = {"Authorization": f"Bearer {org_admin_token(ORG_ID)}"}
    pool = await client.post(
        f"/api/v1/organizations/{ORG_ID}/ipam/pools",
        headers=headers,
        json={"name": "net-pool", "cidr": "10.60.0.0/22"},
    )
    pool_id = pool.json()["id"]

    project = await client.post(
        "/api/v1/projects",
        headers=headers,
        json={"organization_id": ORG_ID, "name": "Net", "slug": "net-ipam"},
    )
    project_id = project.json()["id"]
    agent_id = "ffffffff-ffff-ffff-ffff-ffffffffffff"

    respx.get(f"http://registry.test/api/v1/internal/agents/{agent_id}/connect").mock(
        return_value=Response(
            200,
            json={
                "agent_id": agent_id,
                "organization_id": ORG_ID,
                "base_url": "https://agent.test",
                "agent_token": "tok",
                "tls_verify": False,
            },
        )
    )
    respx.post("https://agent.test/api/v1/networks").mock(
        return_value=Response(
            201,
            json={"name": "lab0", "ipv4_cidr": "10.60.0.0/27", "active": True, "readonly": False},
        )
    )

    created = await client.post(
        f"/api/v1/projects/{project_id}/agents/{agent_id}/networks",
        headers=headers,
        json={"name": "lab0", "ipam": {"pool_id": pool_id, "hosts": 20}},
    )
    assert created.status_code == 201, created.text
    assert created.json()["name"] == "lab0"

    listed = await client.get(
        f"/api/v1/organizations/{ORG_ID}/ipam/pools/{pool_id}/allocations",
        headers=headers,
    )
    assert listed.status_code == 200
    assert any(a["status"] == "allocated" for a in listed.json())


@pytest.mark.asyncio
@respx.mock
async def test_platform_admin_ipam_bypass(client: AsyncClient) -> None:
    from huy_projects.config import get_settings

    get_settings.cache_clear()
    os.environ["IPAM_ENFORCE"] = "true"

    headers = {"Authorization": f"Bearer {platform_token()}"}
    project = await client.post(
        "/api/v1/projects",
        headers=headers,
        json={"organization_id": ORG_ID, "name": "Bypass", "slug": "bypass"},
    )
    project_id = project.json()["id"]
    agent_id = "11111111-1111-1111-1111-111111111112"

    respx.get(f"http://registry.test/api/v1/internal/agents/{agent_id}/connect").mock(
        return_value=Response(
            200,
            json={
                "agent_id": agent_id,
                "organization_id": ORG_ID,
                "base_url": "https://agent.test",
                "agent_token": "tok",
                "tls_verify": False,
            },
        )
    )
    respx.post("https://agent.test/api/v1/networks").mock(
        return_value=Response(201, json={"name": "manual", "ipv4_cidr": "192.168.1.0/24"})
    )

    created = await client.post(
        f"/api/v1/projects/{project_id}/agents/{agent_id}/networks",
        headers=headers,
        json={"name": "manual", "ipv4_cidr": "192.168.1.0/24", "ipam_bypass": True},
    )
    assert created.status_code == 201

    os.environ["IPAM_ENFORCE"] = "false"
    get_settings.cache_clear()
