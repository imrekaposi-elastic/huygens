"""Compliance packs validation unit tests."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from huy_compliance.models import Base
from huy_compliance.schemas import CompliancePackImportIn
from huy_compliance.services import packs_service


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
async def test_validate_pack_rejects_invalid_payload(session: AsyncSession) -> None:
    org_id = "11111111-1111-1111-1111-111111111111"
    body = CompliancePackImportIn(
        pack_key="bad",
        name="Bad",
        vendor="x",
        version="1",
        payload={"standards": "not-a-list"},
    )
    out = await packs_service.validate_pack(session, org_id, body)
    assert out.errors
