"""Infrastructure provider and region CRUD."""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import func, select, update
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


def _collect_subtree_region_ids(
    regions: list[Region], root_region_id: str
) -> set[str]:
    """Region id and all descendants."""
    children_by_parent: dict[str | None, list[str]] = {}
    for r in regions:
        children_by_parent.setdefault(r.parent_region_id, []).append(r.id)
    subtree: set[str] = set()
    stack = [root_region_id]
    while stack:
        rid = stack.pop()
        if rid in subtree:
            continue
        subtree.add(rid)
        stack.extend(children_by_parent.get(rid, []))
    return subtree


def _subtree_delete_order(regions: list[Region], subtree_ids: set[str]) -> list[str]:
    """Deepest regions first so parent deletes do not violate FK constraints."""
    by_id = {r.id: r for r in regions if r.id in subtree_ids}

    def depth(rid: str) -> int:
        r = by_id[rid]
        if r.parent_region_id is None or r.parent_region_id not in subtree_ids:
            return 0
        return 1 + depth(r.parent_region_id)

    return sorted(subtree_ids, key=depth, reverse=True)


async def delete_region(
    session: AsyncSession, infrastructure_provider_id: str, region_id: str
) -> bool:
    region = await get_region(session, infrastructure_provider_id, region_id)
    if region is None:
        return False
    all_regions = await region_tree_service.list_all_regions_for_provider(
        session, infrastructure_provider_id
    )
    subtree_ids = _collect_subtree_region_ids(all_regions, region_id)
    delete_order = _subtree_delete_order(all_regions, subtree_ids)
    await session.execute(
        update(Agent)
        .where(Agent.region_id.in_(delete_order))
        .values(region_id=None)
    )
    for rid in delete_order:
        row = await session.get(Region, rid)
        if row is not None:
            await session.delete(row)
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
    if regions:
        raise HTTPException(
            status_code=409,
            detail="Cannot delete infrastructure provider while it still has regions",
        )
    await session.delete(provider)
    await session.commit()
    return True
