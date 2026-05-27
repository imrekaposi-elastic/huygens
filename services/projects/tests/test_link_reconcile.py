"""Link create → reconcile → connected (mocked agent + breakout-controller)."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock

import pytest
import respx
from httpx import AsyncClient, Request, Response

from helpers import org_admin_token
from test_network_links import ORG_ID, _mock_agent_capabilities, _mock_agent_connect

BREAKOUT_URL = "http://breakout.test"


def _flat_breakout_state(peer_cidr: str) -> dict[str, Any]:
    return {
        "wireguard": {"enabled": False},
        "flat": {
            "enabled": True,
            "mode": "local_peer",
            "nat_exempt_cidrs": [peer_cidr],
            "remote_hypervisor_cidrs": [peer_cidr],
        },
    }


def _patch_local_breakout_proxy(
    proxy: Any, *, left_peer_cidr: str, right_peer_cidr: str
) -> None:
    """Mock agent breakout I/O so drift detection sees expected flat local_peer state."""

    async def get_breakout(_agent_id: str, _org_id: str, name: str) -> dict[str, Any]:
        if name == "net-a":
            return _flat_breakout_state(right_peer_cidr)
        if name == "net-b":
            return _flat_breakout_state(left_peer_cidr)
        raise AssertionError(f"unexpected network {name}")

    proxy.put_wireguard_breakout = AsyncMock(return_value={"enabled": False})
    proxy.put_flat_breakout = AsyncMock(return_value={"enabled": True, "mode": "local_peer"})
    proxy.get_breakout = AsyncMock(side_effect=get_breakout)


def _plan_wireguard_response(body: dict[str, Any]) -> dict[str, Any]:
    """Mirror breakout-controller handlePlan (simplified)."""
    left = body["left"]
    right = body["right"]
    base_port = body.get("listen_port_base") or 51820

    def side(endpoint: dict[str, Any], peer: dict[str, Any], port: int) -> dict[str, Any]:
        allowed = [peer["tunnel_ip"] + "/32"]
        if peer.get("vnet_cidr"):
            allowed.append(peer["vnet_cidr"])
        routes = [endpoint["vnet_cidr"]] if endpoint.get("vnet_cidr") else []
        return {
            "enabled": True,
            "interface": f"wg-{endpoint['network_name']}",
            "listen_port": port,
            "private_key": endpoint["private_key"],
            "address": endpoint["tunnel_ip"] + "/32",
            "vnet_routes": routes,
            "peers": [
                {
                    "name": f"link-{peer['network_name']}",
                    "public_key": peer["public_key"],
                    "allowed_ips": allowed,
                }
            ],
        }

    return {
        "left": side(left, right, base_port),
        "right": side(right, left, base_port + 1),
    }


def _mock_wireguard_breakout_apply(plan: dict[str, Any]) -> None:
    stored = dict(plan)

    def wg_get(request: Request) -> Response:
        parts = request.url.path.rstrip("/").split("/")
        network = parts[-2] if len(parts) >= 2 else ""
        if network == "net-a":
            cfg = stored["left"]
        elif network == "net-b":
            cfg = stored["right"]
        else:
            return Response(404)
        return Response(200, json={"wireguard": cfg, "flat": {"enabled": False}})

    respx.put(url__regex=r"https://agent\.test/api/v1/networks/.+/breakout/wireguard").mock(
        return_value=Response(200, json={"enabled": True})
    )
    respx.get(url__regex=r"https://agent\.test/api/v1/networks/.+/breakout$").mock(
        side_effect=wg_get
    )


@pytest.mark.asyncio
@respx.mock
async def test_local_link_create_then_reconcile_connected(client: AsyncClient) -> None:
    headers = {"Authorization": f"Bearer {org_admin_token(ORG_ID)}"}
    agent_id = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    left_cidr, right_cidr = "10.10.1.0/24", "10.10.2.0/24"

    _mock_agent_connect(agent_id)
    _mock_agent_capabilities()

    p1 = await client.post(
        "/api/v1/projects",
        headers=headers,
        json={"organization_id": ORG_ID, "name": "Recon Local A", "slug": "recon-local-a"},
    )
    p2 = await client.post(
        "/api/v1/projects",
        headers=headers,
        json={"organization_id": ORG_ID, "name": "Recon Local B", "slug": "recon-local-b"},
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
                    desired_state={"ipv4_cidr": left_cidr},
                ),
                ProjectResource(
                    project_id=pid_b,
                    agent_id=agent_id,
                    resource_type="network",
                    name="net-b",
                    desired_state={"ipv4_cidr": right_cidr},
                ),
            ]
        )
        await session.commit()

    created = await client.post(
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
    assert created.status_code == 201, created.text
    link_id = created.json()["id"]
    assert created.json()["status"] == "pending"
    assert created.json()["link_type"] == "local"

    from huy_projects.config import get_settings
    from huy_projects.services.agent_proxy import AgentProxy
    from huy_projects.services.breakout_client import BreakoutControllerClient
    from huy_projects.services.link_reconciler import reconcile_link
    from huy_projects.services.registry_client import RegistryClient

    settings = get_settings()
    proxy = AgentProxy(RegistryClient(settings))
    _patch_local_breakout_proxy(proxy, left_peer_cidr=left_cidr, right_peer_cidr=right_cidr)
    breakout = BreakoutControllerClient(settings)

    async with factory() as session:
        from sqlalchemy import select

        from huy_projects.models import NetworkLink

        result = await session.execute(select(NetworkLink).where(NetworkLink.id == link_id))
        link = result.scalar_one()
        link = await reconcile_link(
            session,
            link,
            proxy=proxy,
            breakout=breakout,
            settings=settings,
            kafka=None,
        )
        assert link.status == "connected", link.last_error
        assert link.config_drift is False
        assert link.applied_generation == link.desired_generation

    detail = await client.get(
        f"/api/v1/organizations/{ORG_ID}/network-links/{link_id}",
        headers=headers,
    )
    assert detail.status_code == 200, detail.text
    assert detail.json()["status"] == "connected"
    assert detail.json()["last_error"] is None


@pytest.mark.asyncio
@respx.mock
async def test_wireguard_link_create_then_reconcile_connected(client: AsyncClient) -> None:
    headers = {"Authorization": f"Bearer {org_admin_token(ORG_ID)}"}
    agent_a = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    agent_b = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"

    _mock_agent_connect(agent_a)
    _mock_agent_connect(agent_b)
    _mock_agent_capabilities()

    pool = await client.post(
        f"/api/v1/organizations/{ORG_ID}/ipam/pools",
        headers=headers,
        json={"name": "recon-overlay", "cidr": "10.255.0.0/24", "pool_kind": "overlay"},
    )
    assert pool.status_code == 201
    pool_id = pool.json()["id"]

    p1 = await client.post(
        "/api/v1/projects",
        headers=headers,
        json={"organization_id": ORG_ID, "name": "Recon WG A", "slug": "recon-wg-a"},
    )
    p2 = await client.post(
        "/api/v1/projects",
        headers=headers,
        json={"organization_id": ORG_ID, "name": "Recon WG B", "slug": "recon-wg-b"},
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

    created = await client.post(
        f"/api/v1/organizations/{ORG_ID}/network-links",
        headers=headers,
        json={
            "overlay_pool_id": pool_id,
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
    assert created.status_code == 201, created.text
    link_id = created.json()["id"]
    assert created.json()["status"] == "pending"
    assert created.json()["link_type"] == "wireguard"

    from huy_projects.config import get_settings
    from huy_projects.services.agent_proxy import AgentProxy
    from huy_projects.services.breakout_client import BreakoutControllerClient
    from huy_projects.services.link_reconciler import reconcile_link
    from huy_projects.services.registry_client import RegistryClient

    settings = get_settings()
    proxy = AgentProxy(RegistryClient(settings))
    breakout = BreakoutControllerClient(settings)

    async with factory() as session:
        from sqlalchemy import select

        from huy_projects.models import NetworkLink

        result = await session.execute(select(NetworkLink).where(NetworkLink.id == link_id))
        link = result.scalar_one()

        def on_plan(request: Request) -> Response:
            body = json.loads(request.content)
            plan = _plan_wireguard_response(body)
            _mock_wireguard_breakout_apply(plan)
            return Response(200, json=plan)

        respx.post(f"{BREAKOUT_URL}/v1/links/plan").mock(side_effect=on_plan)

        await reconcile_link(
            session,
            link,
            proxy=proxy,
            breakout=breakout,
            settings=settings,
            kafka=None,
        )

    detail = await client.get(
        f"/api/v1/organizations/{ORG_ID}/network-links/{link_id}",
        headers=headers,
    )
    assert detail.status_code == 200, detail.text
    body = detail.json()
    assert body["status"] == "connected"
    assert body["last_error"] is None
    assert body["config_drift"] is False
    assert any("/v1/links/plan" in str(c.request.url) for c in respx.calls)

    async with factory() as session:
        from huy_projects.models import NetworkLink

        row = await session.get(NetworkLink, link_id)
        assert row is not None
        assert row.applied_generation == row.desired_generation


@pytest.mark.asyncio
@respx.mock
async def test_wireguard_link_delete_calls_breakout_revoke(client: AsyncClient) -> None:
    headers = {"Authorization": f"Bearer {org_admin_token(ORG_ID)}"}
    agent_a = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    agent_b = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"

    _mock_agent_connect(agent_a)
    _mock_agent_connect(agent_b)
    _mock_agent_capabilities()

    pool = await client.post(
        f"/api/v1/organizations/{ORG_ID}/ipam/pools",
        headers=headers,
        json={"name": "revoke-overlay", "cidr": "10.252.0.0/24", "pool_kind": "overlay"},
    )
    assert pool.status_code == 201
    pool_id = pool.json()["id"]

    p1 = await client.post(
        "/api/v1/projects",
        headers=headers,
        json={"organization_id": ORG_ID, "name": "Revoke A", "slug": "revoke-a"},
    )
    p2 = await client.post(
        "/api/v1/projects",
        headers=headers,
        json={"organization_id": ORG_ID, "name": "Revoke B", "slug": "revoke-b"},
    )
    pid_a, pid_b = p1.json()["id"], p2.json()["id"]

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
                    desired_state={"ipv4_cidr": "10.21.1.0/24"},
                ),
                ProjectResource(
                    project_id=pid_b,
                    agent_id=agent_b,
                    resource_type="network",
                    name="net-b",
                    desired_state={"ipv4_cidr": "10.21.2.0/24"},
                ),
            ]
        )
        await session.commit()

    created = await client.post(
        f"/api/v1/organizations/{ORG_ID}/network-links",
        headers=headers,
        json={
            "overlay_pool_id": pool_id,
            "left": {"agent_id": agent_a, "project_id": pid_a, "network_name": "net-a"},
            "right": {"agent_id": agent_b, "project_id": pid_b, "network_name": "net-b"},
        },
    )
    assert created.status_code == 201
    link_id = created.json()["id"]

    from huy_projects.config import get_settings
    from huy_projects.services.agent_proxy import AgentProxy
    from huy_projects.services.breakout_client import BreakoutControllerClient
    from huy_projects.services.link_reconciler import reconcile_link
    from huy_projects.services.link_service import delete_link
    from huy_projects.services.registry_client import RegistryClient

    settings = get_settings()
    proxy = AgentProxy(RegistryClient(settings))
    proxy.put_wireguard_breakout = AsyncMock(return_value={"enabled": False})
    breakout = BreakoutControllerClient(settings)

    revoke_calls: list[dict[str, Any]] = []

    def on_revoke(request: Request) -> Response:
        revoke_calls.append(json.loads(request.content))
        return Response(200, json={"disabled": True})

    respx.post(f"{BREAKOUT_URL}/v1/links/revoke").mock(side_effect=on_revoke)

    async with factory() as session:
        from sqlalchemy import select

        from huy_projects.models import NetworkLink

        result = await session.execute(select(NetworkLink).where(NetworkLink.id == link_id))
        link = result.scalar_one()
        link.status = "connected"
        await session.commit()

        link = await delete_link(session, link)
        assert link.status == "deleting"

        await reconcile_link(
            session,
            link,
            proxy=proxy,
            breakout=breakout,
            settings=settings,
            kafka=None,
        )

        gone = await session.get(NetworkLink, link_id)
        assert gone is None

    assert len(revoke_calls) == 1
    assert revoke_calls[0]["link_id"] == link_id
    assert revoke_calls[0]["left_network"] == "net-a"
    assert revoke_calls[0]["right_network"] == "net-b"
    assert proxy.put_wireguard_breakout.await_count == 2


@pytest.mark.asyncio
@respx.mock
async def test_local_link_delete_skips_breakout_revoke(client: AsyncClient) -> None:
    headers = {"Authorization": f"Bearer {org_admin_token(ORG_ID)}"}
    agent_id = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    left_cidr, right_cidr = "10.10.3.0/24", "10.10.4.0/24"

    _mock_agent_connect(agent_id)
    _mock_agent_capabilities()
    respx.post(f"{BREAKOUT_URL}/v1/links/revoke").mock(
        return_value=Response(500, json={"detail": "should not be called"})
    )

    p1 = await client.post(
        "/api/v1/projects",
        headers=headers,
        json={"organization_id": ORG_ID, "name": "LocalDel A", "slug": "localdel-a"},
    )
    p2 = await client.post(
        "/api/v1/projects",
        headers=headers,
        json={"organization_id": ORG_ID, "name": "LocalDel B", "slug": "localdel-b"},
    )
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
                    desired_state={"ipv4_cidr": left_cidr},
                ),
                ProjectResource(
                    project_id=pid_b,
                    agent_id=agent_id,
                    resource_type="network",
                    name="net-b",
                    desired_state={"ipv4_cidr": right_cidr},
                ),
            ]
        )
        await session.commit()

    created = await client.post(
        f"/api/v1/organizations/{ORG_ID}/network-links",
        headers=headers,
        json={
            "left": {"agent_id": agent_id, "project_id": pid_a, "network_name": "net-a"},
            "right": {"agent_id": agent_id, "project_id": pid_b, "network_name": "net-b"},
        },
    )
    link_id = created.json()["id"]

    from huy_projects.config import get_settings
    from huy_projects.services.agent_proxy import AgentProxy
    from huy_projects.services.breakout_client import BreakoutControllerClient
    from huy_projects.services.link_reconciler import reconcile_link
    from huy_projects.services.link_service import delete_link
    from huy_projects.services.registry_client import RegistryClient

    settings = get_settings()
    proxy = AgentProxy(RegistryClient(settings))
    _patch_local_breakout_proxy(proxy, left_peer_cidr=left_cidr, right_peer_cidr=right_cidr)
    breakout = BreakoutControllerClient(settings)

    async with factory() as session:
        from sqlalchemy import select

        from huy_projects.models import NetworkLink

        result = await session.execute(select(NetworkLink).where(NetworkLink.id == link_id))
        link = result.scalar_one()
        link = await delete_link(session, link)
        await reconcile_link(
            session,
            link,
            proxy=proxy,
            breakout=breakout,
            settings=settings,
            kafka=None,
        )
        assert await session.get(NetworkLink, link_id) is None

    assert not any("/v1/links/revoke" in str(c.request.url) for c in respx.calls)
