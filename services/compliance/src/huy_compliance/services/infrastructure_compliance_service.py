"""Infrastructure provider and region compliance (catalog item links)."""

from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from huy_compliance.models import (
    InfrastructureProviderCompliance,
    InfrastructureProviderComplianceItemLink,
    RegionComplianceItemLink,
)
from huy_compliance.schemas import (
    ComplianceItemOut,
    InfrastructureProviderComplianceOut,
    InfrastructureProviderComplianceSet,
    RegionComplianceOut,
    RegionComplianceSet,
)
from huy_compliance.services import audit, catalog_service


async def get_provider_compliance(
    session: AsyncSession, organization_id: str, provider_id: str
) -> InfrastructureProviderComplianceOut:
    row = await session.scalar(
        select(InfrastructureProviderCompliance)
        .where(
            InfrastructureProviderCompliance.organization_id == organization_id,
            InfrastructureProviderCompliance.infrastructure_provider_id == provider_id,
        )
        .options(selectinload(InfrastructureProviderCompliance.item_links))
    )
    if row is None:
        return InfrastructureProviderComplianceOut(
            organization_id=organization_id,
            infrastructure_provider_id=provider_id,
            is_compliant=False,
            compliance_items=[],
            updated_at=None,
        )
    item_ids = [link.compliance_item_id for link in row.item_links]
    items = await catalog_service._load_items_by_ids(session, organization_id, item_ids)
    # Compliant when at least one catalog standard is active on the provider.
    is_compliant = len(items) > 0
    return InfrastructureProviderComplianceOut(
        organization_id=organization_id,
        infrastructure_provider_id=provider_id,
        is_compliant=is_compliant,
        compliance_items=[catalog_service._item_out(i) for i in items],
        updated_at=row.updated_at,
    )


async def set_provider_compliance(
    session: AsyncSession,
    organization_id: str,
    provider_id: str,
    body: InfrastructureProviderComplianceSet,
    *,
    actor_user_id: str,
) -> InfrastructureProviderComplianceOut:
    if body.compliance_item_ids:
        await catalog_service._load_items_by_ids(
            session, organization_id, body.compliance_item_ids
        )
    row = await session.scalar(
        select(InfrastructureProviderCompliance)
        .where(
            InfrastructureProviderCompliance.organization_id == organization_id,
            InfrastructureProviderCompliance.infrastructure_provider_id == provider_id,
        )
        .options(selectinload(InfrastructureProviderCompliance.item_links))
    )
    if row is None:
        row = InfrastructureProviderCompliance(
            organization_id=organization_id,
            infrastructure_provider_id=provider_id,
        )
        session.add(row)
        await session.flush()
    row.is_compliant = (
        body.is_compliant if body.is_compliant is not None else bool(body.compliance_item_ids)
    )
    await session.execute(
        delete(InfrastructureProviderComplianceItemLink).where(
            InfrastructureProviderComplianceItemLink.profile_id == row.id
        )
    )
    for item_id in dict.fromkeys(body.compliance_item_ids):
        session.add(
            InfrastructureProviderComplianceItemLink(
                profile_id=row.id,
                compliance_item_id=item_id,
            )
        )
    await session.flush()
    await audit.record_audit(
        session,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        action="infrastructure_provider.compliance.set",
        entity_type="infrastructure_provider",
        entity_id=provider_id,
        detail=f"compliant={body.is_compliant} items={len(body.compliance_item_ids)}",
    )
    return await get_provider_compliance(session, organization_id, provider_id)


async def get_region_compliance(
    session: AsyncSession, organization_id: str, region_id: str
) -> RegionComplianceOut:
    links = (
        await session.scalars(
            select(RegionComplianceItemLink).where(
                RegionComplianceItemLink.organization_id == organization_id,
                RegionComplianceItemLink.region_id == region_id,
            )
        )
    ).all()
    item_ids = [link.compliance_item_id for link in links]
    items = await catalog_service._load_items_by_ids(session, organization_id, item_ids)
    return RegionComplianceOut(
        organization_id=organization_id,
        region_id=region_id,
        compliance_items=[catalog_service._item_out(i) for i in items],
    )


async def set_region_compliance(
    session: AsyncSession,
    organization_id: str,
    region_id: str,
    body: RegionComplianceSet,
    *,
    actor_user_id: str,
) -> RegionComplianceOut:
    if body.compliance_item_ids:
        await catalog_service._load_items_by_ids(
            session, organization_id, body.compliance_item_ids
        )
    existing = (
        await session.scalars(
            select(RegionComplianceItemLink).where(
                RegionComplianceItemLink.organization_id == organization_id,
                RegionComplianceItemLink.region_id == region_id,
            )
        )
    ).all()
    for link in existing:
        await session.delete(link)
    for item_id in dict.fromkeys(body.compliance_item_ids):
        session.add(
            RegionComplianceItemLink(
                organization_id=organization_id,
                region_id=region_id,
                compliance_item_id=item_id,
            )
        )
    await session.flush()
    await audit.record_audit(
        session,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        action="region.compliance.set",
        entity_type="region",
        entity_id=region_id,
        detail=f"items={len(body.compliance_item_ids)}",
    )
    return await get_region_compliance(session, organization_id, region_id)


async def catalog_items_for_provider(
    session: AsyncSession, organization_id: str, provider_id: str
) -> list[ComplianceItemOut]:
    profile = await get_provider_compliance(session, organization_id, provider_id)
    return profile.compliance_items


async def catalog_items_for_region(
    session: AsyncSession, organization_id: str, region_id: str
) -> list[ComplianceItemOut]:
    region = await get_region_compliance(session, organization_id, region_id)
    return region.compliance_items


async def catalog_items_for_region_lineage(
    session: AsyncSession,
    organization_id: str,
    ancestry_ids: list[str],
) -> list[tuple[str, ComplianceItemOut]]:
    """Catalog items from the agent region and each ancestor (nearest first).

    Returns (source_region_id, item) so callers can attribute inherited standards.
    """
    out: list[tuple[str, ComplianceItemOut]] = []
    seen_item_ids: set[str] = set()
    for region_id in ancestry_ids:
        for item in await catalog_items_for_region(session, organization_id, region_id):
            if item.id in seen_item_ids:
                continue
            seen_item_ids.add(item.id)
            out.append((region_id, item))
    return out
