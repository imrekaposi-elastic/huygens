"""Proxied flat breakout API (Phase 6.1)."""

from __future__ import annotations

import pytest
import respx
from httpx import AsyncClient, Response

from helpers import auditor_token, org_admin_token, operator_token

ORG_ID = "11111111-1111-1111-1111-111111111111"


@pytest.mark.asyncio
@respx.mock
async def test_get_and_put_flat_breakout_proxy(client: AsyncClient) -> None:
    headers = {"Authorization": f"Bearer {org_admin_token(ORG_ID)}"}
    project = await client.post(
        "/api/v1/projects",
        headers=headers,
        json={"organization_id": ORG_ID, "name": "Breakout", "slug": "breakout-ui"},
    )
    assert project.status_code == 201
    project_id = project.json()["id"]
    agent_id = "cccccccc-cccc-cccc-cccc-cccccccccccc"
    net = "lab-net"

    respx.get(f"http://registry.test/api/v1/internal/agents/{agent_id}/connect").mock(
        return_value=Response(
            200,
            json={
                "agent_id": agent_id,
                "organization_id": ORG_ID,
                "base_url": "https://agent.test",
                "agent_token": "agent-secret",
                "tls_verify": False,
            },
        )
    )
    respx.get(f"https://agent.test/api/v1/networks/{net}").mock(
        return_value=Response(
            200,
            json={"name": net, "active": True, "ipv4_cidr": "10.10.1.0/24"},
        )
    )
    respx.get(f"https://agent.test/api/v1/networks/{net}/breakout").mock(
        return_value=Response(
            200,
            json={
                "wireguard": {"enabled": False},
                "flat": {"enabled": False, "mode": "bridge_uplink", "uplink": ""},
            },
        )
    )
    put_route = respx.put(f"https://agent.test/api/v1/networks/{net}/breakout/flat").mock(
        return_value=Response(
            200,
            json={
                "wireguard": {"enabled": False},
                "flat": {
                    "enabled": True,
                    "mode": "bridge_uplink",
                    "uplink": "eth0",
                    "remote_hypervisor_cidrs": [],
                    "nat_exempt_cidrs": [],
                },
            },
        )
    )

    await client.post(
        f"/api/v1/projects/{project_id}/agents/{agent_id}/assignments",
        headers=headers,
        json={"resource_type": "network", "name": net},
    )

    got = await client.get(
        f"/api/v1/projects/{project_id}/agents/{agent_id}/networks/{net}/breakout",
        headers=headers,
    )
    assert got.status_code == 200
    assert got.json()["flat"]["enabled"] is False

    put = await client.put(
        f"/api/v1/projects/{project_id}/agents/{agent_id}/networks/{net}/breakout/flat",
        headers=headers,
        json={
            "enabled": True,
            "mode": "bridge_uplink",
            "uplink": "eth0",
            "remote_hypervisor_cidrs": [],
            "nat_exempt_cidrs": [],
        },
    )
    assert put.status_code == 200, put.text
    assert put.json()["flat"]["uplink"] == "eth0"
    assert put_route.called


@pytest.mark.asyncio
@respx.mock
async def test_auditor_can_read_breakout_operator_can_write(client: AsyncClient) -> None:
    headers = {"Authorization": f"Bearer {org_admin_token(ORG_ID)}"}
    project = await client.post(
        "/api/v1/projects",
        headers=headers,
        json={"organization_id": ORG_ID, "name": "Breakout RBAC", "slug": "breakout-rbac"},
    )
    project_id = project.json()["id"]
    agent_id = "dddddddd-dddd-dddd-dddd-dddddddddddd"
    net = "rbac-net"

    respx.get(f"http://registry.test/api/v1/internal/agents/{agent_id}/connect").mock(
        return_value=Response(
            200,
            json={
                "agent_id": agent_id,
                "organization_id": ORG_ID,
                "base_url": "https://agent.test",
                "agent_token": "secret",
                "tls_verify": False,
            },
        )
    )
    respx.get(f"https://agent.test/api/v1/networks/{net}").mock(
        return_value=Response(200, json={"name": net, "active": True})
    )
    respx.get(f"https://agent.test/api/v1/networks/{net}/breakout").mock(
        return_value=Response(
            200,
            json={"wireguard": {"enabled": False}, "flat": {"enabled": False, "uplink": ""}},
        )
    )
    respx.put(f"https://agent.test/api/v1/networks/{net}/breakout/flat").mock(
        return_value=Response(200, json={"wireguard": {"enabled": False}, "flat": {"enabled": True}})
    )

    await client.post(
        f"/api/v1/projects/{project_id}/agents/{agent_id}/assignments",
        headers=headers,
        json={"resource_type": "network", "name": net},
    )

    aud = {"Authorization": f"Bearer {auditor_token(ORG_ID, project_id)}"}
    read = await client.get(
        f"/api/v1/projects/{project_id}/agents/{agent_id}/networks/{net}/breakout",
        headers=aud,
    )
    assert read.status_code == 200

    op = {"Authorization": f"Bearer {operator_token(ORG_ID, project_id)}"}
    write = await client.put(
        f"/api/v1/projects/{project_id}/agents/{agent_id}/networks/{net}/breakout/flat",
        headers=op,
        json={"enabled": True, "mode": "macvlan", "uplink": "eth1"},
    )
    assert write.status_code == 200
