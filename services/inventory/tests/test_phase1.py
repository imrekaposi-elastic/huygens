"""Phase 1 inventory tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt
import pytest
import respx
from httpx import AsyncClient, Response

from huy_inventory.config import get_settings
from huy_inventory.db import get_session_factory
from huy_inventory.services.poller_loop import InventoryPoller
from huy_inventory.services.snapshot_service import get_snapshot


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


@respx.mock
@pytest.mark.asyncio
async def test_poller_stores_snapshot(client: AsyncClient) -> None:
    settings = get_settings()
    org_id = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    agent_id = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
    base = "https://agent.test"

    respx.get(f"{settings.registry_url}/api/v1/internal/poll-targets").mock(
        return_value=Response(
            200,
            json=[
                {
                    "agent_id": agent_id,
                    "organization_id": org_id,
                    "region_id": "cccccccc-cccc-cccc-cccc-cccccccccccc",
                    "base_url": base,
                    "agent_token": "secret",
                    "refresh_seconds": 30,
                    "tls_verify": False,
                }
            ],
        )
    )
    respx.patch(f"{settings.registry_url}/api/v1/internal/agents/{agent_id}/poll-status").mock(
        return_value=Response(204)
    )
    respx.get(f"{base}/api/v1/agent").mock(
        return_value=Response(
            200,
            json={
                "hostname": "hv1",
                "version": "0.1.0",
                "settings": {"country": "NL", "city": "AMS", "company": "T"},
                "libvirt_uri": "qemu:///system",
                "data_dir": "/var/lib",
                "tls": {"enabled": True, "scheme": "https"},
            },
        )
    )
    respx.get(f"{base}/api/v1/vms").mock(return_value=Response(200, json=[]))
    respx.get(f"{base}/api/v1/networks").mock(
        return_value=Response(
            200,
            json=[{"name": "default", "active": True, "readonly": True, "deletable": False}],
        )
    )

    poller = InventoryPoller(settings, get_session_factory())
    await poller.poll_once()

    async with get_session_factory()() as session:
        snap = await get_snapshot(session, agent_id)
    assert snap is not None
    assert snap.poll_error is None
    assert snap.payload["networks"][0]["name"] == "default"

    headers = {"Authorization": f"Bearer {_platform_token()}"}
    listed = await client.get("/api/v1/inventory/agents", headers=headers)
    assert listed.status_code == 200
    assert listed.json()[0]["vm_count"] == 0

    dash = await client.get(f"/api/v1/inventory/organizations/{org_id}/dashboard", headers=headers)
    assert dash.status_code == 200
    assert dash.json()["agent_count"] == 1
