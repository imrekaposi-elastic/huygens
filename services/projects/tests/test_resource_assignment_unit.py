"""Resource assignment service unit tests."""

from __future__ import annotations

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from huy_projects.models import Base, Project
from huy_projects.services import project_service, resource_assignment_service


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
async def test_assign_and_unassign_resource(session: AsyncSession) -> None:
    from huy_projects.schemas import ProjectCreate

    project = await project_service.create_project(
        session,
        ProjectCreate(organization_id="org-1", name="P", slug="p"),
    )
    row = await resource_assignment_service.assign_resource(
        session,
        project,
        agent_id="agent-1",
        resource_type="network",
        name="net-a",
        actual_state={"ipv4_cidr": "10.0.0.0/24"},
    )
    assert row.name == "net-a"

    assignments = await resource_assignment_service.list_org_resource_assignments(
        session, "org-1"
    )
    assert len(assignments) == 1

    await resource_assignment_service.unassign_resource(
        session,
        project,
        agent_id="agent-1",
        resource_type="network",
        name="net-a",
    )
    assert not await resource_assignment_service.list_org_resource_assignments(
        session, "org-1"
    )


@pytest.mark.asyncio
async def test_assign_rejects_system_network(session: AsyncSession) -> None:
    from huy_projects.schemas import ProjectCreate

    project = await project_service.create_project(
        session,
        ProjectCreate(organization_id="org-1", name="P", slug="p"),
    )
    with pytest.raises(HTTPException) as exc:
        await resource_assignment_service.assign_resource(
            session,
            project,
            agent_id="agent-1",
            resource_type="network",
            name="default",
            actual_state={},
        )
    assert exc.value.status_code == 400
