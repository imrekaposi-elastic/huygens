"""Project service unit tests."""

from __future__ import annotations

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from huy_projects.models import Base, Project
from huy_projects.schemas import ProjectCreate, ProjectUpdate
from huy_projects.services import project_service


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
async def test_create_project_duplicate_slug(session: AsyncSession) -> None:
    body = ProjectCreate(organization_id="org-1", name="One", slug="one")
    await project_service.create_project(session, body)
    with pytest.raises(HTTPException) as exc:
        await project_service.create_project(session, body)
    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_update_and_list_projects(session: AsyncSession) -> None:
    created = await project_service.create_project(
        session,
        ProjectCreate(organization_id="org-1", name="Alpha", slug="alpha"),
    )
    updated = await project_service.update_project(
        session,
        created,
        ProjectUpdate(name="Alpha Beta", description="desc"),
    )
    assert updated.name == "Alpha Beta"
    assert updated.description == "desc"

    listed = await project_service.list_projects(session, organization_id="org-1")
    assert len(listed) == 1
    assert project_service.project_to_out(listed[0]).slug == "alpha"


@pytest.mark.asyncio
async def test_delete_project(session: AsyncSession) -> None:
    created = await project_service.create_project(
        session,
        ProjectCreate(organization_id="org-1", name="Gone", slug="gone"),
    )
    await project_service.delete_project(session, created)
    assert await project_service.get_project(session, created.id) is None
