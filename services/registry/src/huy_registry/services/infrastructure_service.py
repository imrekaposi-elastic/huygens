"""Infrastructure provider and region CRUD."""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from huy_registry.models import Agent, InfrastructureProvider, Region
from huy_registry.schemas import InfrastructureProviderCreate, RegionCreate
from huy_registry.services import region_tree_service


async def create_infrastructure_provider(
    session: AsyncSession, body: InfrastructureProviderCreate
) -> InfrastructureProvider:
    existing = await session.execute(
        select(InfrastructureProvider).where(InfrastructureProvider.slug == body.slug)
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="Infrastructure provider slug already exists")
    row = InfrastructureProvider(name=body.name, slug=body.slug)
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


async def list_infrastructure_providers(session: AsyncSession) -> list[InfrastructureProvider]:
    result = await session.execute(
        select(InfrastructureProvider).order_by(InfrastructureProvider.name)
    )
    return list(result.scalars().all())


async def get_infrastructure_provider(
    session: AsyncSession, infrastructure_provider_id: str
) -> InfrastructureProvider | None:
    return await session.get(InfrastructureProvider, infrastructure_provider_id)


async def create_region(
    session: AsyncSession,
    infrastructure_provider_id: str,
    body: RegionCreate,
) -> Region:
    provider = await session.get(InfrastructureProvider, infrastructure_provider_id)
    if provider is None:
        raise HTTPException(status_code=404, detail="Infrastructure provider not found")
    if body.parent_region_id is not None:
        parent = await session.get(Region, body.parent_region_id)
        if parent is None or parent.infrastructure_provider_id != infrastructure_provider_id:
            raise HTTPException(status_code=400, detail="Invalid parent_region_id for provider")
    existing = await session.execute(
        select(Region).where(
            Region.infrastructure_provider_id == infrastructure_provider_id,
            Region.parent_region_id == body.parent_region_id,
            Region.slug == body.slug,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="Region slug already exists under this parent")
    row = Region(
        infrastructure_provider_id=infrastructure_provider_id,
        parent_region_id=body.parent_region_id,
        name=body.name,
        slug=body.slug,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


async def list_root_regions(session: AsyncSession, infrastructure_provider_id: str) -> list[Region]:
    result = await session.execute(
        select(Region)
        .where(
            Region.infrastructure_provider_id == infrastructure_provider_id,
            Region.parent_region_id.is_(None),
        )
        .order_by(Region.name)
    )
    return list(result.scalars().all())


async def get_region(
    session: AsyncSession, infrastructure_provider_id: str, region_id: str
) -> Region | None:
    result = await session.execute(
        select(Region).where(
            Region.id == region_id,
            Region.infrastructure_provider_id == infrastructure_provider_id,
        )
    )
    return result.scalar_one_or_none()


async def _agent_count_for_region(session: AsyncSession, region_id: str) -> int:
    return int(
        await session.scalar(
            select(func.count()).select_from(Agent).where(Agent.region_id == region_id)
        )
        or 0
    )


async def _child_region_count(session: AsyncSession, region_id: str) -> int:
    return int(
        await session.scalar(
            select(func.count())
            .select_from(Region)
            .where(Region.parent_region_id == region_id)
        )
        or 0
    )


async def delete_region(
    session: AsyncSession, infrastructure_provider_id: str, region_id: str
) -> bool:
    region = await get_region(session, infrastructure_provider_id, region_id)
    if region is None:
        return False
    if await _agent_count_for_region(session, region_id) > 0:
        raise HTTPException(
            status_code=409,
            detail="Cannot delete region while agents are enrolled on it",
        )
    if await _child_region_count(session, region_id) > 0:
        raise HTTPException(
            status_code=409,
            detail="Cannot delete region while sub-regions exist",
        )
    await session.delete(region)
    await session.commit()
    return True


async def delete_infrastructure_provider(
    session: AsyncSession, infrastructure_provider_id: str
) -> bool:
    provider = await get_infrastructure_provider(session, infrastructure_provider_id)
    if provider is None:
        return False
    agents = await region_tree_service.list_agents_for_provider(session, infrastructure_provider_id)
    if agents:
        raise HTTPException(
            status_code=409,
            detail="Cannot delete infrastructure provider while agents reference it",
        )
    regions = await region_tree_service.list_all_regions_for_provider(
        session, infrastructure_provider_id
    )
    for region in sorted(regions, key=lambda r: r.parent_region_id or "", reverse=True):
        await session.delete(region)
    await session.delete(provider)
    await session.commit()
    return True
