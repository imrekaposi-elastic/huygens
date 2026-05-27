"""Compliance catalog, traits, checks, assignments."""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from huy_compliance.models import (
    ensure_utc,
    AssetCriticalityAssignment,
    AssetCriticalityItemLink,
    ComplianceCheck,
    OrgComplianceItem,
    ProviderTrait,
    RegionTrait,
    utc_now,
)
from huy_compliance.resource_keys import ResourceRef
from huy_compliance.schemas import (
    AssetCriticalityOut,
    AssetCriticalitySet,
    ComplianceCheckCreate,
    ComplianceCheckOut,
    ComplianceCheckUpdate,
    ComplianceDashboardOut,
    ComplianceItemCreate,
    ComplianceItemOut,
    ComplianceItemUpdate,
    TraitCreate,
    TraitOut,
)
from huy_compliance.services import audit


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug[:64] or "item"


def _item_out(row: OrgComplianceItem) -> ComplianceItemOut:
    return ComplianceItemOut(
        id=row.id,
        organization_id=row.organization_id,
        name=row.name,
        slug=row.slug,
        description=row.description,
        reference_url=row.reference_url,
        moscow=row.moscow,
        target_level=row.target_level,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


async def list_catalog(session: AsyncSession, organization_id: str) -> list[ComplianceItemOut]:
    rows = (
        await session.scalars(
            select(OrgComplianceItem)
            .where(OrgComplianceItem.organization_id == organization_id)
            .order_by(OrgComplianceItem.name)
        )
    ).all()
    return [_item_out(r) for r in rows]


async def create_catalog_item(
    session: AsyncSession,
    organization_id: str,
    body: ComplianceItemCreate,
    *,
    actor_user_id: str,
) -> ComplianceItemOut:
    slug = body.slug or _slugify(body.name)
    existing = await session.scalar(
        select(OrgComplianceItem).where(
            OrgComplianceItem.organization_id == organization_id,
            OrgComplianceItem.slug == slug,
        )
    )
    if existing:
        raise HTTPException(status_code=409, detail=f"Catalog slug '{slug}' already exists")
    row = OrgComplianceItem(
        organization_id=organization_id,
        name=body.name,
        slug=slug,
        description=body.description,
        reference_url=body.reference_url,
        moscow=body.moscow,
        target_level=body.target_level,
    )
    session.add(row)
    await session.flush()
    await audit.record_audit(
        session,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        action="catalog.create",
        entity_type="compliance_item",
        entity_id=row.id,
        detail=row.name,
    )
    return _item_out(row)


async def update_catalog_item(
    session: AsyncSession,
    organization_id: str,
    item_id: str,
    body: ComplianceItemUpdate,
    *,
    actor_user_id: str,
) -> ComplianceItemOut:
    row = await session.get(OrgComplianceItem, item_id)
    if row is None or row.organization_id != organization_id:
        raise HTTPException(status_code=404, detail="Compliance item not found")
    if body.name is not None:
        row.name = body.name
    if body.description is not None:
        row.description = body.description
    if body.reference_url is not None:
        row.reference_url = body.reference_url
    if body.moscow is not None:
        row.moscow = body.moscow
    if body.target_level is not None:
        row.target_level = body.target_level
    row.updated_at = utc_now()
    await audit.record_audit(
        session,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        action="catalog.update",
        entity_type="compliance_item",
        entity_id=row.id,
    )
    return _item_out(row)


async def delete_catalog_item(
    session: AsyncSession,
    organization_id: str,
    item_id: str,
    *,
    actor_user_id: str,
) -> None:
    row = await session.get(OrgComplianceItem, item_id)
    if row is None or row.organization_id != organization_id:
        raise HTTPException(status_code=404, detail="Compliance item not found")
    await session.delete(row)
    await audit.record_audit(
        session,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        action="catalog.delete",
        entity_type="compliance_item",
        entity_id=item_id,
    )


async def list_provider_traits(
    session: AsyncSession, organization_id: str, provider_id: str
) -> list[TraitOut]:
    rows = (
        await session.scalars(
            select(ProviderTrait).where(
                ProviderTrait.organization_id == organization_id,
                ProviderTrait.infrastructure_provider_id == provider_id,
            )
        )
    ).all()
    return [
        TraitOut(
            id=r.id,
            organization_id=r.organization_id,
            trait_key=r.trait_key,
            title=r.title,
            description=r.description,
            moscow=r.moscow,
            infrastructure_provider_id=r.infrastructure_provider_id,
            created_at=r.created_at,
        )
        for r in rows
    ]


async def create_provider_trait(
    session: AsyncSession,
    organization_id: str,
    provider_id: str,
    body: TraitCreate,
    *,
    actor_user_id: str,
) -> TraitOut:
    row = ProviderTrait(
        organization_id=organization_id,
        infrastructure_provider_id=provider_id,
        trait_key=body.trait_key,
        title=body.title,
        description=body.description,
        moscow=body.moscow,
    )
    session.add(row)
    await session.flush()
    await audit.record_audit(
        session,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        action="trait.create",
        entity_type="provider_trait",
        entity_id=row.id,
    )
    return TraitOut(
        id=row.id,
        organization_id=row.organization_id,
        trait_key=row.trait_key,
        title=row.title,
        description=row.description,
        moscow=row.moscow,
        infrastructure_provider_id=row.infrastructure_provider_id,
        created_at=row.created_at,
    )


async def delete_provider_trait(
    session: AsyncSession,
    organization_id: str,
    trait_id: str,
    *,
    actor_user_id: str,
) -> None:
    row = await session.get(ProviderTrait, trait_id)
    if row is None or row.organization_id != organization_id:
        raise HTTPException(status_code=404, detail="Provider trait not found")
    await session.delete(row)
    await audit.record_audit(
        session,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        action="trait.delete",
        entity_type="provider_trait",
        entity_id=trait_id,
    )


async def list_region_traits(
    session: AsyncSession, organization_id: str, region_id: str
) -> list[TraitOut]:
    rows = (
        await session.scalars(
            select(RegionTrait).where(
                RegionTrait.organization_id == organization_id,
                RegionTrait.region_id == region_id,
            )
        )
    ).all()
    return [
        TraitOut(
            id=r.id,
            organization_id=r.organization_id,
            trait_key=r.trait_key,
            title=r.title,
            description=r.description,
            moscow=r.moscow,
            region_id=r.region_id,
            created_at=r.created_at,
        )
        for r in rows
    ]


async def create_region_trait(
    session: AsyncSession,
    organization_id: str,
    region_id: str,
    body: TraitCreate,
    *,
    actor_user_id: str,
) -> TraitOut:
    row = RegionTrait(
        organization_id=organization_id,
        region_id=region_id,
        trait_key=body.trait_key,
        title=body.title,
        description=body.description,
        moscow=body.moscow,
    )
    session.add(row)
    await session.flush()
    await audit.record_audit(
        session,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        action="trait.create",
        entity_type="region_trait",
        entity_id=row.id,
    )
    return TraitOut(
        id=row.id,
        organization_id=row.organization_id,
        trait_key=row.trait_key,
        title=row.title,
        description=row.description,
        moscow=row.moscow,
        region_id=row.region_id,
        created_at=row.created_at,
    )


async def delete_region_trait(
    session: AsyncSession,
    organization_id: str,
    trait_id: str,
    *,
    actor_user_id: str,
) -> None:
    row = await session.get(RegionTrait, trait_id)
    if row is None or row.organization_id != organization_id:
        raise HTTPException(status_code=404, detail="Region trait not found")
    await session.delete(row)
    await audit.record_audit(
        session,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        action="trait.delete",
        entity_type="region_trait",
        entity_id=trait_id,
    )


async def _load_items_by_ids(
    session: AsyncSession, organization_id: str, item_ids: list[str]
) -> list[OrgComplianceItem]:
    if not item_ids:
        return []
    rows = (
        await session.scalars(
            select(OrgComplianceItem).where(
                OrgComplianceItem.organization_id == organization_id,
                OrgComplianceItem.id.in_(item_ids),
            )
        )
    ).all()
    if len(rows) != len(set(item_ids)):
        raise HTTPException(status_code=400, detail="Unknown compliance_item_id in assignment")
    return list(rows)


async def get_asset_criticality(
    session: AsyncSession,
    organization_id: str,
    ref: ResourceRef,
) -> AssetCriticalityOut:
    row = await session.scalar(
        select(AssetCriticalityAssignment)
        .where(
            AssetCriticalityAssignment.organization_id == organization_id,
            AssetCriticalityAssignment.resource_type == ref.resource_type,
            AssetCriticalityAssignment.resource_key == ref.key(),
        )
        .options(selectinload(AssetCriticalityAssignment.item_links))
    )
    items: list[OrgComplianceItem] = []
    note = None
    updated_at = None
    if row:
        item_ids = [link.compliance_item_id for link in row.item_links]
        items = await _load_items_by_ids(session, organization_id, item_ids)
        note = row.placement_note
        updated_at = row.updated_at
    return AssetCriticalityOut(
        organization_id=organization_id,
        resource_type=ref.resource_type,  # type: ignore[arg-type]
        project_id=ref.project_id,
        agent_id=ref.agent_id,
        name=ref.name,
        compliance_items=[_item_out(i) for i in items],
        placement_note=note,
        updated_at=updated_at,
    )


async def set_asset_criticality(
    session: AsyncSession,
    organization_id: str,
    ref: ResourceRef,
    body: AssetCriticalitySet,
    *,
    actor_user_id: str,
) -> AssetCriticalityOut:
    items = await _load_items_by_ids(session, organization_id, body.compliance_item_ids)
    row = await session.scalar(
        select(AssetCriticalityAssignment)
        .where(
            AssetCriticalityAssignment.organization_id == organization_id,
            AssetCriticalityAssignment.resource_type == ref.resource_type,
            AssetCriticalityAssignment.resource_key == ref.key(),
        )
        .options(selectinload(AssetCriticalityAssignment.item_links))
    )
    if row is None:
        row = AssetCriticalityAssignment(
            organization_id=organization_id,
            resource_type=ref.resource_type,
            resource_key=ref.key(),
            placement_note=body.placement_note,
            updated_by=actor_user_id,
        )
        session.add(row)
        await session.flush()
    else:
        row.placement_note = body.placement_note
        row.updated_by = actor_user_id
        row.updated_at = utc_now()
        await session.execute(
            delete(AssetCriticalityItemLink).where(
                AssetCriticalityItemLink.assignment_id == row.id
            )
        )
    for item in items:
        session.add(AssetCriticalityItemLink(assignment_id=row.id, compliance_item_id=item.id))
    await audit.record_audit(
        session,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        action="criticality.set",
        entity_type=ref.resource_type,
        entity_id=row.id,
        detail=ref.key(),
    )
    return await get_asset_criticality(session, organization_id, ref)


def _check_out(row: ComplianceCheck, item_name: str | None = None) -> ComplianceCheckOut:
    now = utc_now()
    days = (ensure_utc(row.valid_until) - now).days if row.valid_until else None
    return ComplianceCheckOut(
        id=row.id,
        organization_id=row.organization_id,
        compliance_item_id=row.compliance_item_id,
        compliance_item_name=item_name,
        owner_user_id=row.owner_user_id,
        owner_display=row.owner_display,
        valid_until=row.valid_until,
        status=row.status,
        last_reviewed_at=row.last_reviewed_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
        days_until_expiry=days,
    )


async def list_checks(session: AsyncSession, organization_id: str) -> list[ComplianceCheckOut]:
    result = await session.execute(
        select(ComplianceCheck, OrgComplianceItem.name)
        .join(OrgComplianceItem, OrgComplianceItem.id == ComplianceCheck.compliance_item_id)
        .where(ComplianceCheck.organization_id == organization_id)
        .order_by(ComplianceCheck.valid_until)
    )
    return [_check_out(check, name) for check, name in result.all()]


async def create_check(
    session: AsyncSession,
    organization_id: str,
    body: ComplianceCheckCreate,
    *,
    actor_user_id: str,
) -> ComplianceCheckOut:
    item = await session.get(OrgComplianceItem, body.compliance_item_id)
    if item is None or item.organization_id != organization_id:
        raise HTTPException(status_code=400, detail="Unknown compliance_item_id")
    row = ComplianceCheck(
        organization_id=organization_id,
        compliance_item_id=body.compliance_item_id,
        owner_user_id=body.owner_user_id,
        owner_display=body.owner_display,
        valid_until=ensure_utc(body.valid_until),
        status=body.status,
    )
    session.add(row)
    await session.flush()
    await audit.record_audit(
        session,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        action="check.create",
        entity_type="compliance_check",
        entity_id=row.id,
    )
    return _check_out(row, item.name)


async def update_check(
    session: AsyncSession,
    organization_id: str,
    check_id: str,
    body: ComplianceCheckUpdate,
    *,
    actor_user_id: str,
) -> ComplianceCheckOut:
    row = await session.get(ComplianceCheck, check_id)
    if row is None or row.organization_id != organization_id:
        raise HTTPException(status_code=404, detail="Compliance check not found")
    if body.owner_user_id is not None:
        row.owner_user_id = body.owner_user_id
    if body.owner_display is not None:
        row.owner_display = body.owner_display
    if body.valid_until is not None:
        row.valid_until = ensure_utc(body.valid_until)
    if body.status is not None:
        row.status = body.status
    if body.last_reviewed_at is not None:
        row.last_reviewed_at = body.last_reviewed_at
    row.updated_at = utc_now()
    item = await session.get(OrgComplianceItem, row.compliance_item_id)
    await audit.record_audit(
        session,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        action="check.update",
        entity_type="compliance_check",
        entity_id=row.id,
    )
    return _check_out(row, item.name if item else None)


async def delete_check(
    session: AsyncSession,
    organization_id: str,
    check_id: str,
    *,
    actor_user_id: str,
) -> None:
    row = await session.get(ComplianceCheck, check_id)
    if row is None or row.organization_id != organization_id:
        raise HTTPException(status_code=404, detail="Compliance check not found")
    await session.delete(row)
    await audit.record_audit(
        session,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        action="check.delete",
        entity_type="compliance_check",
        entity_id=check_id,
    )


async def dashboard(session: AsyncSession, organization_id: str) -> ComplianceDashboardOut:
    now = utc_now()
    soon = now + timedelta(days=30)
    catalog_count = await session.scalar(
        select(func.count())
        .select_from(OrgComplianceItem)
        .where(OrgComplianceItem.organization_id == organization_id)
    )
    checks = (
        await session.scalars(
            select(ComplianceCheck).where(ComplianceCheck.organization_id == organization_id)
        )
    ).all()
    active = sum(1 for c in checks if c.status == "active")
    expiring = sum(
        1
        for c in checks
        if c.status == "active"
        and ensure_utc(c.valid_until) <= soon
        and ensure_utc(c.valid_until) >= now
    )
    expired = sum(
        1 for c in checks if ensure_utc(c.valid_until) < now or c.status == "expired"
    )
    assignments_count = await session.scalar(
        select(func.count())
        .select_from(AssetCriticalityAssignment)
        .where(AssetCriticalityAssignment.organization_id == organization_id)
    )
    from huy_compliance.models import (
        InfrastructureProviderCompliance,
        InfrastructureProviderComplianceItemLink,
        RegionComplianceItemLink,
    )

    provider_traits_count = await session.scalar(
        select(func.count())
        .select_from(InfrastructureProviderComplianceItemLink)
        .join(
            InfrastructureProviderCompliance,
            InfrastructureProviderCompliance.id
            == InfrastructureProviderComplianceItemLink.profile_id,
        )
        .where(InfrastructureProviderCompliance.organization_id == organization_id)
    )
    region_traits_count = await session.scalar(
        select(func.count())
        .select_from(RegionComplianceItemLink)
        .where(RegionComplianceItemLink.organization_id == organization_id)
    )
    return ComplianceDashboardOut(
        organization_id=organization_id,
        catalog_count=int(catalog_count or 0),
        checks_active=active,
        checks_expiring_soon=expiring,
        checks_expired=expired,
        assignments_count=int(assignments_count or 0),
        provider_traits_count=int(provider_traits_count or 0),
        region_traits_count=int(region_traits_count or 0),
    )
