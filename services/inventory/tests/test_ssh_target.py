"""SSH target resolution tests."""

from __future__ import annotations

import pytest
import respx
from httpx import AsyncClient, Response

from huy_inventory.config import get_settings
from huy_inventory.db import get_session_factory
from huy_inventory.services.ssh_target_service import (
    _relay_host_from_agent_url,
    _relay_ws_url_from_agent_url,
    resolve_ssh_target,
)


def test_relay_urls_from_agent_base() -> None:
    assert _relay_host_from_agent_url("https://dommel.example:8765") == "dommel.example"
    assert (
        _relay_ws_url_from_agent_url("https://dommel.example:8765")
        == "wss://dommel.example:8765/api/v1/ssh/relay/ws"
    )
    assert _relay_ws_url_from_agent_url("http://127.0.0.1:8765") == "ws://127.0.0.1:8765/api/v1/ssh/relay/ws"


@respx.mock
@pytest.mark.asyncio
async def test_resolve_ssh_target(client: AsyncClient) -> None:
    settings = get_settings()
    org_id = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    project_id = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
    agent_id = "cccccccc-cccc-cccc-cccc-cccccccccccc"
    vm_name = "web-01"

    respx.get(
        f"{settings.projects_url}/api/v1/internal/organizations/{org_id}/resource-assignments"
    ).mock(
        return_value=Response(
            200,
            json=[
                {
                    "agent_id": agent_id,
                    "resource_type": "vm",
                    "name": vm_name,
                    "project_id": project_id,
                }
            ],
        )
    )
    respx.get(f"{settings.registry_url}/api/v1/internal/poll-targets").mock(
        return_value=Response(
            200,
            json=[
                {
                    "agent_id": agent_id,
                    "base_url": "https://agent.test:8765",
                    "organization_id": org_id,
                }
            ],
        )
    )

    factory = get_session_factory()
    async with factory() as session:
        from huy_inventory.services.snapshot_service import upsert_snapshot

        await upsert_snapshot(
            session,
            agent_id=agent_id,
            organization_id=org_id,
            region_id="eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee",
            payload={
                "vms": [
                    {
                        "name": vm_name,
                        "ips": ["10.0.0.5"],
                        "guest_status": "running",
                    }
                ],
                "networks": [],
            },
            poll_error=None,
        )
        await session.commit()
        target = await resolve_ssh_target(
            session,
            settings,
            organization_id=org_id,
            project_id=project_id,
            vm_name=vm_name,
        )
    assert target["guest_ip"] == "10.0.0.5"
    assert target["relay_host"] == "agent.test"
    assert target["ssh_ready"] is True


@respx.mock
@pytest.mark.asyncio
async def test_internal_ssh_target_route(client: AsyncClient) -> None:
    settings = get_settings()
    org_id = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    project_id = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
    agent_id = "dddddddd-dddd-dddd-dddd-dddddddddddd"
    vm_name = "app-01"

    respx.get(
        f"{settings.projects_url}/api/v1/internal/organizations/{org_id}/resource-assignments"
    ).mock(
        return_value=Response(
            200,
            json=[
                {
                    "agent_id": agent_id,
                    "resource_type": "vm",
                    "name": vm_name,
                    "project_id": project_id,
                }
            ],
        )
    )
    respx.get(f"{settings.registry_url}/api/v1/internal/poll-targets").mock(
        return_value=Response(
            200,
            json=[{"agent_id": agent_id, "base_url": "https://hv.test", "organization_id": org_id}],
        )
    )

    factory = get_session_factory()
    async with factory() as session:
        from huy_inventory.services.snapshot_service import upsert_snapshot

        await upsert_snapshot(
            session,
            agent_id=agent_id,
            organization_id=org_id,
            region_id="eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee",
            payload={"vms": [{"name": vm_name, "ips": ["192.168.1.10"]}], "networks": []},
            poll_error=None,
        )
        await session.commit()

    r = await client.get(
        "/internal/v1/ssh/target",
        headers={"X-Huy-Service-Token": "test-inventory-service-token"},
        params={
            "organization_id": org_id,
            "project_id": project_id,
            "vm_name": vm_name,
        },
    )
    assert r.status_code == 200, r.text
    assert r.json()["vm_name"] == vm_name
