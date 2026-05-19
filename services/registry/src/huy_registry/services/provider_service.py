"""Provider and region CRUD."""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from huy_registry.models import Provider, Region
from huy_registry.schemas import ProviderCreate, RegionCreate


async def create_provider(session: AsyncSession, body: ProviderCreate) -> Provider:
    existing = await session.execute(select(Provider).where(Provider.slug == body.slug))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="Provider slug already exists")
    row = Provider(name=body.name, slug=body.slug)
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


async def list_providers(session: AsyncSession) -> list[Provider]:
    result = await session.execute(select(Provider).order_by(Provider.name))
    return list(result.scalars().all())


async def get_provider(session: AsyncSession, provider_id: str) -> Provider | None:
    return await session.get(Provider, provider_id)


async def create_region(session: AsyncSession, provider_id: str, body: RegionCreate) -> Region:
    provider = await session.get(Provider, provider_id)
    if provider is None:
        raise HTTPException(status_code=404, detail="Provider not found")
    existing = await session.execute(
        select(Region).where(Region.provider_id == provider_id, Region.slug == body.slug)
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="Region slug already exists for provider")
    row = Region(provider_id=provider_id, name=body.name, slug=body.slug)
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


async def list_regions(session: AsyncSession, provider_id: str) -> list[Region]:
    result = await session.execute(
        select(Region).where(Region.provider_id == provider_id).order_by(Region.name)
    )
    return list(result.scalars().all())
