"""Network delete guard unit tests."""

from __future__ import annotations

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from huy_projects.models import Base, NetworkLink, Project
from huy_projects.services.network_delete_guard import (
    _active_links_for_endpoint,
    _breakout_is_active,
    assert_network_deletable,
)


def test_breakout_is_active_detects_wireguard() -> None:
    assert _breakout_is_active({"wireguard": {"enabled": True}, "flat": {}}) is True
    assert _breakout_is_active({"wireguard": {}, "flat": {}}) is False


@pytest.fixture
async def session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as sess:
        yield sess
    await engine.dispose()


@pytest.mark.asyncio
async def test_active_links_for_endpoint(session: AsyncSession) -> None:
    project = Project(organization_id="org-1", name="P", slug="p")
    session.add(project)
    await session.flush()
    session.add(
        NetworkLink(
            organization_id="org-1",
            name="link-1",
            left_agent_id="a1",
            left_project_id=project.id,
            left_network_name="net-a",
            right_agent_id="a2",
            right_project_id=project.id,
            right_network_name="net-b",
            status="active",
            tunnel_cidr="10.255.0.0/30",
            left_tunnel_address="10.255.0.1",
            right_tunnel_address="10.255.0.2",
            overlay_pool_id="pool-1",
            left_public_key="lpk",
            right_public_key="rpk",
            left_private_key_enc="lenc",
            right_private_key_enc="renc",
        )
    )
    await session.commit()

    links = await _active_links_for_endpoint(
        session,
        "org-1",
        agent_id="a1",
        project_id=project.id,
        network_name="net-a",
    )
    assert len(links) == 1


class _ProxyStub:
    def __init__(self, *, vms: list[dict] | None = None, breakout: dict | None = None) -> None:
        self._vms = vms if vms is not None else [{"name": "web-01", "network": "net-a"}]
        self._breakout = breakout or {"wireguard": {"enabled": False}, "flat": {"enabled": False}}

    async def list_vms(self, agent_id: str, organization_id: str) -> list[dict]:
        return self._vms

    async def get_breakout(self, agent_id: str, organization_id: str, network_name: str) -> dict:
        return self._breakout


@pytest.mark.asyncio
async def test_assert_network_deletable_blocks_vms(session: AsyncSession) -> None:
    project = Project(organization_id="org-1", name="P", slug="p")
    session.add(project)
    await session.commit()

    with pytest.raises(HTTPException) as exc:
        await assert_network_deletable(
            session,
            _ProxyStub(),
            project,
            agent_id="a1",
            network_name="net-a",
        )
    assert exc.value.status_code == 409
    assert "VM" in exc.value.detail


@pytest.mark.asyncio
async def test_assert_network_deletable_blocks_active_breakout(session: AsyncSession) -> None:
    project = Project(organization_id="org-1", name="P", slug="p")
    session.add(project)
    await session.commit()

    proxy = _ProxyStub(
        vms=[],
        breakout={"wireguard": {"enabled": True}, "flat": {"enabled": False}},
    )
    with pytest.raises(HTTPException) as exc:
        await assert_network_deletable(
            session,
            proxy,
            project,
            agent_id="a1",
            network_name="net-a",
        )
    assert exc.value.status_code == 409
    assert "breakout" in exc.value.detail.lower()
