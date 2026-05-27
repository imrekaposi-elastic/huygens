"""Network link and overlay IPAM API tests."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from helpers import auditor_token, org_admin_token, operator_token

ORG_ID = "11111111-1111-1111-1111-111111111111"


@pytest.mark.asyncio
async def test_overlay_pool_and_topology_empty(client: AsyncClient) -> None:
    headers = {"Authorization": f"Bearer {org_admin_token(ORG_ID)}"}
    pool = await client.post(
        f"/api/v1/organizations/{ORG_ID}/ipam/pools",
        headers=headers,
        json={
            "name": "overlay-pool",
            "cidr": "10.255.0.0/24",
            "pool_kind": "overlay",
        },
    )
    assert pool.status_code == 201, pool.text
    assert pool.json()["pool_kind"] == "overlay"

    topo = await client.get(
        f"/api/v1/organizations/{ORG_ID}/topology",
        headers=headers,
    )
    assert topo.status_code == 200
    body = topo.json()
    assert body["organization_id"] == ORG_ID
    assert body["vnets"] == []
    assert body["links"] == []


@pytest.mark.asyncio
async def test_auditor_can_read_topology(client: AsyncClient) -> None:
    project = await client.post(
        "/api/v1/projects",
        headers={"Authorization": f"Bearer {org_admin_token(ORG_ID)}"},
        json={
            "organization_id": ORG_ID,
            "name": "Topo Read",
            "slug": "topo-read",
        },
    )
    assert project.status_code == 201
    project_id = project.json()["id"]
    headers = {"Authorization": f"Bearer {auditor_token(ORG_ID, project_id)}"}
    topo = await client.get(
        f"/api/v1/organizations/{ORG_ID}/topology",
        headers=headers,
    )
    assert topo.status_code == 200


@pytest.mark.asyncio
async def test_operator_cannot_create_link_without_both_projects(client: AsyncClient) -> None:
    headers = {"Authorization": f"Bearer {org_admin_token(ORG_ID)}"}
    overlay = await client.post(
        f"/api/v1/organizations/{ORG_ID}/ipam/pools",
        headers=headers,
        json={"name": "ov2", "cidr": "10.254.0.0/24", "pool_kind": "overlay"},
    )
    assert overlay.status_code == 201
    pool_id = overlay.json()["id"]

    p1 = await client.post(
        "/api/v1/projects",
        headers=headers,
        json={"organization_id": ORG_ID, "name": "Link A", "slug": "link-a"},
    )
    p2 = await client.post(
        "/api/v1/projects",
        headers=headers,
        json={"organization_id": ORG_ID, "name": "Link B", "slug": "link-b"},
    )
    assert p1.status_code == 201 and p2.status_code == 201
    pid_a, pid_b = p1.json()["id"], p2.json()["id"]

    op_headers = {"Authorization": f"Bearer {operator_token(ORG_ID, pid_a)}"}
    link = await client.post(
        f"/api/v1/organizations/{ORG_ID}/network-links",
        headers=op_headers,
        json={
            "overlay_pool_id": pool_id,
            "left": {
                "agent_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                "project_id": pid_a,
                "network_name": "net-a",
            },
            "right": {
                "agent_id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
                "project_id": pid_b,
                "network_name": "net-b",
            },
        },
    )
    assert link.status_code == 403


@pytest.mark.asyncio
async def test_same_agent_link_creates_local_without_overlay(client: AsyncClient) -> None:
    headers = {"Authorization": f"Bearer {org_admin_token(ORG_ID)}"}
    agent_id = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"

    p1 = await client.post(
        "/api/v1/projects",
        headers=headers,
        json={"organization_id": ORG_ID, "name": "Local A", "slug": "local-a"},
    )
    p2 = await client.post(
        "/api/v1/projects",
        headers=headers,
        json={"organization_id": ORG_ID, "name": "Local B", "slug": "local-b"},
    )
    assert p1.status_code == 201 and p2.status_code == 201
    pid_a, pid_b = p1.json()["id"], p2.json()["id"]

    from huy_projects.db import get_session_factory
    from huy_projects.models import ProjectResource

    factory = get_session_factory()
    async with factory() as session:
        session.add_all(
            [
                ProjectResource(
                    project_id=pid_a,
                    agent_id=agent_id,
                    resource_type="network",
                    name="net-a",
                    desired_state={"ipv4_cidr": "10.10.1.0/24"},
                ),
                ProjectResource(
                    project_id=pid_b,
                    agent_id=agent_id,
                    resource_type="network",
                    name="net-b",
                    desired_state={"ipv4_cidr": "10.10.2.0/24"},
                ),
            ]
        )
        await session.commit()

    link = await client.post(
        f"/api/v1/organizations/{ORG_ID}/network-links",
        headers=headers,
        json={
            "left": {
                "agent_id": agent_id,
                "project_id": pid_a,
                "network_name": "net-a",
            },
            "right": {
                "agent_id": agent_id,
                "project_id": pid_b,
                "network_name": "net-b",
            },
        },
    )
    assert link.status_code == 201, link.text
    body = link.json()
    assert body["link_type"] == "local"
    assert body["left_tunnel_address"] == "10.10.1.0/24"
    assert body["right_tunnel_address"] == "10.10.2.0/24"
    assert body["tunnel_cidr"] == "direct"

    topo = await client.get(
        f"/api/v1/organizations/{ORG_ID}/topology",
        headers=headers,
    )
    assert topo.status_code == 200
    edges = topo.json()["links"]
    assert len(edges) == 1
    assert edges[0]["link_type"] == "local"


@pytest.mark.asyncio
async def test_cross_agent_link_requires_overlay_pool(client: AsyncClient) -> None:
    headers = {"Authorization": f"Bearer {org_admin_token(ORG_ID)}"}
    p1 = await client.post(
        "/api/v1/projects",
        headers=headers,
        json={"organization_id": ORG_ID, "name": "WG A", "slug": "wg-a"},
    )
    p2 = await client.post(
        "/api/v1/projects",
        headers=headers,
        json={"organization_id": ORG_ID, "name": "WG B", "slug": "wg-b"},
    )
    assert p1.status_code == 201 and p2.status_code == 201
    pid_a, pid_b = p1.json()["id"], p2.json()["id"]
    agent_a = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    agent_b = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"

    from huy_projects.db import get_session_factory
    from huy_projects.models import ProjectResource

    factory = get_session_factory()
    async with factory() as session:
        session.add_all(
            [
                ProjectResource(
                    project_id=pid_a,
                    agent_id=agent_a,
                    resource_type="network",
                    name="net-a",
                    desired_state={"ipv4_cidr": "10.20.1.0/24"},
                ),
                ProjectResource(
                    project_id=pid_b,
                    agent_id=agent_b,
                    resource_type="network",
                    name="net-b",
                    desired_state={"ipv4_cidr": "10.20.2.0/24"},
                ),
            ]
        )
        await session.commit()

    link = await client.post(
        f"/api/v1/organizations/{ORG_ID}/network-links",
        headers=headers,
        json={
            "left": {
                "agent_id": agent_a,
                "project_id": pid_a,
                "network_name": "net-a",
            },
            "right": {
                "agent_id": agent_b,
                "project_id": pid_b,
                "network_name": "net-b",
            },
        },
    )
    assert link.status_code == 400
    assert "overlay_pool_id" in link.json()["detail"]
