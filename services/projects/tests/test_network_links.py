"""Network link and overlay IPAM API tests."""

from __future__ import annotations

import pytest
import respx
from httpx import AsyncClient, Response

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


def _mock_agent_connect(agent_id: str) -> None:
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


def _mock_agent_capabilities(
    *,
    flat_local_peer: bool = True,
    wireguard: bool = True,
) -> None:
    caps: list[str] = []
    if wireguard:
        caps.append("wireguard.breakout")
    if flat_local_peer:
        caps.append("flat_breakout.local_peer")
    respx.get("https://agent.test/api/v1/agent").mock(
        return_value=Response(200, json={"capabilities": caps})
    )


@pytest.mark.asyncio
@respx.mock
async def test_same_agent_link_creates_local_without_overlay(client: AsyncClient) -> None:
    headers = {"Authorization": f"Bearer {org_admin_token(ORG_ID)}"}
    agent_id = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    _mock_agent_connect(agent_id)
    _mock_agent_capabilities()

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


@pytest.mark.asyncio
@respx.mock
async def test_local_link_rejected_when_agent_lacks_local_peer_capability(
    client: AsyncClient,
) -> None:
    headers = {"Authorization": f"Bearer {org_admin_token(ORG_ID)}"}
    agent_id = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    _mock_agent_connect(agent_id)
    _mock_agent_capabilities(flat_local_peer=False)

    p1 = await client.post(
        "/api/v1/projects",
        headers=headers,
        json={"organization_id": ORG_ID, "name": "Cap A", "slug": "cap-a"},
    )
    p2 = await client.post(
        "/api/v1/projects",
        headers=headers,
        json={"organization_id": ORG_ID, "name": "Cap B", "slug": "cap-b"},
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
                    desired_state={"ipv4_cidr": "10.11.1.0/24"},
                ),
                ProjectResource(
                    project_id=pid_b,
                    agent_id=agent_id,
                    resource_type="network",
                    name="net-b",
                    desired_state={"ipv4_cidr": "10.11.2.0/24"},
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
    assert link.status_code == 400
    assert "flat_breakout.local_peer" in link.json()["detail"]


@pytest.mark.asyncio
@respx.mock
async def test_delete_network_rejected_when_topology_link_exists(client: AsyncClient) -> None:
    headers = {"Authorization": f"Bearer {org_admin_token(ORG_ID)}"}
    agent_id = "99999999-9999-9999-9999-999999999999"
    _mock_agent_connect(agent_id)
    respx.get("https://agent.test/api/v1/networks/net-a").mock(
        return_value=Response(200, json={"name": "net-a", "deletable": True})
    )
    respx.delete("https://agent.test/api/v1/networks/net-a").mock(
        return_value=Response(204)
    )

    p1 = await client.post(
        "/api/v1/projects",
        headers=headers,
        json={"organization_id": ORG_ID, "name": "LinkDel A", "slug": "linkdel-a"},
    )
    p2 = await client.post(
        "/api/v1/projects",
        headers=headers,
        json={"organization_id": ORG_ID, "name": "LinkDel B", "slug": "linkdel-b"},
    )
    assert p1.status_code == 201 and p2.status_code == 201
    pid_a, pid_b = p1.json()["id"], p2.json()["id"]

    from huy_projects.db import get_session_factory
    from huy_projects.models import NetworkLink, ProjectResource

    factory = get_session_factory()
    async with factory() as session:
        session.add_all(
            [
                ProjectResource(
                    project_id=pid_a,
                    agent_id=agent_id,
                    resource_type="network",
                    name="net-a",
                    desired_state={"ipv4_cidr": "10.12.1.0/24"},
                ),
                ProjectResource(
                    project_id=pid_b,
                    agent_id=agent_id,
                    resource_type="network",
                    name="net-b",
                    desired_state={"ipv4_cidr": "10.12.2.0/24"},
                ),
            ]
        )
        session.add(
            NetworkLink(
                organization_id=ORG_ID,
                name="local-test",
                status="connected",
                link_type="local",
                left_agent_id=agent_id,
                left_project_id=pid_a,
                left_network_name="net-a",
                right_agent_id=agent_id,
                right_project_id=pid_b,
                right_network_name="net-b",
                overlay_pool_id="00000000-0000-0000-0000-000000000000",
                tunnel_cidr="direct",
                left_tunnel_address="10.12.1.0/24",
                right_tunnel_address="10.12.2.0/24",
                left_public_key="",
                right_public_key="",
                left_private_key_enc="enc",
                right_private_key_enc="enc",
                left_vnet_cidr="10.12.1.0/24",
                right_vnet_cidr="10.12.2.0/24",
            )
        )
        await session.commit()

    deleted = await client.delete(
        f"/api/v1/projects/{pid_a}/agents/{agent_id}/networks/net-a",
        headers=headers,
    )
    assert deleted.status_code == 409
    assert "topology link" in deleted.json()["detail"].lower()

    links = await client.get(
        f"/api/v1/organizations/{ORG_ID}/network-links",
        headers=headers,
    )
    assert links.status_code == 200
    assert links.json()[0]["status"] == "connected"


@pytest.mark.asyncio
@respx.mock
async def test_assignment_reconciler_prunes_stale_network(client: AsyncClient) -> None:
    from huy_projects.db import get_session_factory
    from huy_projects.models import ProjectResource
    from huy_projects.services.agent_proxy import AgentProxy
    from huy_projects.services.assignment_reconciler import reconcile_stale_network_assignments
    from huy_projects.services.registry_client import RegistryClient
    from huy_projects.config import get_settings

    headers = {"Authorization": f"Bearer {org_admin_token(ORG_ID)}"}
    agent_id = "88888888-8888-8888-8888-888888888888"
    project = await client.post(
        "/api/v1/projects",
        headers=headers,
        json={"organization_id": ORG_ID, "name": "Reconcile", "slug": "reconcile"},
    )
    project_id = project.json()["id"]
    _mock_agent_connect(agent_id)
    respx.get("https://agent.test/api/v1/networks").mock(
        return_value=Response(200, json=[{"name": "other-net"}])
    )

    factory = get_session_factory()
    async with factory() as session:
        session.add(
            ProjectResource(
                project_id=project_id,
                agent_id=agent_id,
                resource_type="network",
                name="gone-net",
                desired_state={"ipv4_cidr": "10.13.0.0/24"},
            )
        )
        await session.commit()

    settings = get_settings()
    proxy = AgentProxy(RegistryClient(settings))
    async with factory() as session:
        removed = await reconcile_stale_network_assignments(session, proxy=proxy)
        assert removed == 1

    async with factory() as session:
        from sqlalchemy import select

        rows = await session.execute(
            select(ProjectResource).where(
                ProjectResource.project_id == project_id,
                ProjectResource.name == "gone-net",
            )
        )
        assert rows.scalars().all() == []


def test_format_reconcile_error_local_peer_hint() -> None:
    from fastapi import HTTPException

    from huy_projects.services.link_reconciler import _format_reconcile_error

    exc = HTTPException(
        status_code=422,
        detail='{"detail":[{"loc":["body","mode"],"msg":"literal_error","input":"local_peer"}]}',
    )
    msg = _format_reconcile_error(exc)
    assert "upgrade libvirt agent" in msg
    assert "local_peer" in msg
