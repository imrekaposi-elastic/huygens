"""SSE auth: no query-string JWT; Bearer header required."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from httpx import ASGITransport, AsyncClient

from huy_auth.auth_context import AuthContext, OrgMembership
from huy_inventory.api.routes.events import _sse_generator
from huy_inventory.config import get_settings
from huy_inventory.services.sse_hub import get_event_hub, reset_event_hub_for_tests
from huy_inventory.services.sse_kafka import user_may_receive_event


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


@pytest.fixture
async def sse_client() -> AsyncClient:
    get_settings.cache_clear()
    reset_event_hub_for_tests()
    from huy_inventory.main import create_app

    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        async with app.router.lifespan_context(app):
            yield ac


@pytest.mark.asyncio
async def test_sse_rejects_token_query_param(sse_client: AsyncClient) -> None:
    r = await sse_client.get(
        "/api/v1/inventory/events/stream?token=leaked-jwt",
        headers={"Authorization": f"Bearer {_platform_token()}"},
    )
    assert r.status_code == 400
    assert "query" in r.json()["detail"].lower()
    assert "Authorization" in r.json()["detail"]


@pytest.mark.asyncio
async def test_sse_rejects_access_token_query_param(sse_client: AsyncClient) -> None:
    r = await sse_client.get("/api/v1/inventory/events/stream?access_token=secret")
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_sse_requires_bearer_header(sse_client: AsyncClient) -> None:
    r = await sse_client.get("/api/v1/inventory/events/stream")
    assert r.status_code == 401


def test_user_may_receive_event_org_scope() -> None:
    org_id = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    envelope = {
        "data": {"organization_id": org_id},
    }
    admin = AuthContext(
        user_id="1",
        email="a@b.com",
        username="admin",
        platform_roles=["platform_admin"],
    )
    member = AuthContext(
        user_id="2",
        email="m@b.com",
        username="member",
        org_memberships=[OrgMembership(organization_id=org_id, roles=["admin"])],
    )
    outsider = AuthContext(
        user_id="3",
        email="o@b.com",
        username="outsider",
        org_memberships=[OrgMembership(organization_id="other-org", roles=["admin"])],
    )
    assert user_may_receive_event(admin, envelope) is True
    assert user_may_receive_event(member, envelope) is True
    assert user_may_receive_event(outsider, envelope) is False


@pytest.mark.asyncio
async def test_sse_generator_emits_published_event() -> None:
    reset_event_hub_for_tests()
    org_id = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    user = AuthContext(
        user_id="1",
        email="a@b.com",
        username="admin",
        platform_roles=["platform_admin"],
    )
    envelope = {
        "type": "com.huygens.inventory.snapshot.v1",
        "data": {"organization_id": org_id, "agent_id": "agent-1"},
    }
    gen = _sse_generator(user)
    connected = await gen.__anext__()
    assert connected.startswith(":")

    hub = get_event_hub()
    next_chunk = asyncio.create_task(gen.__anext__())
    await hub.publish(envelope)
    chunk = await asyncio.wait_for(next_chunk, timeout=2.0)
    assert "event: com.huygens.inventory.snapshot.v1" in chunk
    assert org_id in chunk
    await gen.aclose()
