"""Qualitative characteristics (Phase 7+ successor to legacy traits)."""

from __future__ import annotations

import re

from fastapi import HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from huy_compliance.models import (
    InfrastructureProviderCharacteristicLink,
    OrgQualitativeCharacteristic,
    ProviderTrait,
    RegionCharacteristicLink,
    RegionTrait,
    utc_now,
)
from huy_compliance.schemas import (
    CharacteristicLinkSet,
    LegacyTraitsMigrateOut,
    QualitativeCharacteristicCreate,
    QualitativeCharacteristicOut,
    QualitativeCharacteristicUpdate,
)
from huy_compliance.services import audit


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug[:64] or "characteristic"


def _out(row: OrgQualitativeCharacteristic) -> QualitativeCharacteristicOut:
    return QualitativeCharacteristicOut(
        id=row.id,
        organization_id=row.organization_id,
        name=row.name,
        slug=row.slug,
        description=row.description,
        moscow=row.moscow,
        kind=row.kind,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


async def list_characteristics(
    session: AsyncSession, organization_id: str
) -> list[QualitativeCharacteristicOut]:
    rows = (
        await session.scalars(
            select(OrgQualitativeCharacteristic)
            .where(OrgQualitativeCharacteristic.organization_id == organization_id)
            .order_by(OrgQualitativeCharacteristic.name)
        )
    ).all()
    return [_out(r) for r in rows]


async def create_characteristic(
    session: AsyncSession,
    organization_id: str,
    body: QualitativeCharacteristicCreate,
    *,
    actor_user_id: str,
) -> QualitativeCharacteristicOut:
    slug = body.slug or _slugify(body.name)
    existing = await session.scalar(
        select(OrgQualitativeCharacteristic).where(
            OrgQualitativeCharacteristic.organization_id == organization_id,
            OrgQualitativeCharacteristic.slug == slug,
        )
    )
    if existing:
        raise HTTPException(status_code=409, detail=f"Characteristic slug '{slug}' already exists")
    row = OrgQualitativeCharacteristic(
        organization_id=organization_id,
        name=body.name,
        slug=slug,
        description=body.description,
        moscow=body.moscow,
        kind=body.kind,
    )
    session.add(row)
    await session.flush()
    await audit.record_audit(
        session,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        action="characteristic.create",
        entity_type="qualitative_characteristic",
        entity_id=row.id,
        detail=row.name,
    )
    return _out(row)


async def update_characteristic(
    session: AsyncSession,
    organization_id: str,
    characteristic_id: str,
    body: QualitativeCharacteristicUpdate,
    *,
    actor_user_id: str,
) -> QualitativeCharacteristicOut:
    row = await session.get(OrgQualitativeCharacteristic, characteristic_id)
    if row is None or row.organization_id != organization_id:
        raise HTTPException(status_code=404, detail="Characteristic not found")
    if body.name is not None:
        row.name = body.name
    if body.description is not None:
        row.description = body.description
    if body.moscow is not None:
        row.moscow = body.moscow
    if body.kind is not None:
        row.kind = body.kind
    row.updated_at = utc_now()
    await audit.record_audit(
        session,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        action="characteristic.update",
        entity_type="qualitative_characteristic",
        entity_id=row.id,
    )
    return _out(row)


async def delete_characteristic(
    session: AsyncSession,
    organization_id: str,
    characteristic_id: str,
    *,
    actor_user_id: str,
) -> None:
    row = await session.get(OrgQualitativeCharacteristic, characteristic_id)
    if row is None or row.organization_id != organization_id:
        raise HTTPException(status_code=404, detail="Characteristic not found")
    await session.delete(row)
    await audit.record_audit(
        session,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        action="characteristic.delete",
        entity_type="qualitative_characteristic",
        entity_id=characteristic_id,
    )


async def set_provider_characteristics(
    session: AsyncSession,
    organization_id: str,
    provider_id: str,
    body: CharacteristicLinkSet,
    *,
    actor_user_id: str,
) -> None:
    # Validate characteristic IDs exist for org.
    if body.characteristic_ids:
        rows = (
            await session.scalars(
                select(OrgQualitativeCharacteristic.id).where(
                    OrgQualitativeCharacteristic.organization_id == organization_id,
                    OrgQualitativeCharacteristic.id.in_(body.characteristic_ids),
                )
            )
        ).all()
        if len(rows) != len(set(body.characteristic_ids)):
            raise HTTPException(status_code=400, detail="Unknown characteristic_id in set")
    await session.execute(
        delete(InfrastructureProviderCharacteristicLink).where(
            InfrastructureProviderCharacteristicLink.organization_id == organization_id,
            InfrastructureProviderCharacteristicLink.infrastructure_provider_id == provider_id,
        )
    )
    for cid in body.characteristic_ids:
        session.add(
            InfrastructureProviderCharacteristicLink(
                organization_id=organization_id,
                infrastructure_provider_id=provider_id,
                characteristic_id=cid,
            )
        )
    await audit.record_audit(
        session,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        action="characteristic.set_provider",
        entity_type="infrastructure_provider",
        entity_id=provider_id,
    )


async def set_region_characteristics(
    session: AsyncSession,
    organization_id: str,
    region_id: str,
    body: CharacteristicLinkSet,
    *,
    actor_user_id: str,
) -> None:
    if body.characteristic_ids:
        rows = (
            await session.scalars(
                select(OrgQualitativeCharacteristic.id).where(
                    OrgQualitativeCharacteristic.organization_id == organization_id,
                    OrgQualitativeCharacteristic.id.in_(body.characteristic_ids),
                )
            )
        ).all()
        if len(rows) != len(set(body.characteristic_ids)):
            raise HTTPException(status_code=400, detail="Unknown characteristic_id in set")
    await session.execute(
        delete(RegionCharacteristicLink).where(
            RegionCharacteristicLink.organization_id == organization_id,
            RegionCharacteristicLink.region_id == region_id,
        )
    )
    for cid in body.characteristic_ids:
        session.add(
            RegionCharacteristicLink(
                organization_id=organization_id,
                region_id=region_id,
                characteristic_id=cid,
            )
        )
    await audit.record_audit(
        session,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        action="characteristic.set_region",
        entity_type="region",
        entity_id=region_id,
    )


async def get_provider_characteristic_ids(
    session: AsyncSession, organization_id: str, provider_id: str
) -> list[str]:
    ids = (
        await session.scalars(
            select(InfrastructureProviderCharacteristicLink.characteristic_id).where(
                InfrastructureProviderCharacteristicLink.organization_id == organization_id,
                InfrastructureProviderCharacteristicLink.infrastructure_provider_id == provider_id,
            )
        )
    ).all()
    return list(ids)


async def get_region_characteristic_ids(
    session: AsyncSession, organization_id: str, region_id: str
) -> list[str]:
    ids = (
        await session.scalars(
            select(RegionCharacteristicLink.characteristic_id).where(
                RegionCharacteristicLink.organization_id == organization_id,
                RegionCharacteristicLink.region_id == region_id,
            )
        )
    ).all()
    return list(ids)


async def provider_characteristics(
    session: AsyncSession, organization_id: str, provider_id: str
) -> list[OrgQualitativeCharacteristic]:
    rows = (
        await session.scalars(
            select(OrgQualitativeCharacteristic)
            .join(
                InfrastructureProviderCharacteristicLink,
                InfrastructureProviderCharacteristicLink.characteristic_id
                == OrgQualitativeCharacteristic.id,
            )
            .where(
                InfrastructureProviderCharacteristicLink.organization_id == organization_id,
                InfrastructureProviderCharacteristicLink.infrastructure_provider_id == provider_id,
            )
            .order_by(OrgQualitativeCharacteristic.name)
        )
    ).all()
    return list(rows)


async def _get_or_create_characteristic_for_trait(
    session: AsyncSession,
    organization_id: str,
    *,
    slug: str,
    name: str,
    description: str | None,
    moscow: str,
    char_by_slug: dict[str, OrgQualitativeCharacteristic],
) -> tuple[OrgQualitativeCharacteristic, bool]:
    existing = char_by_slug.get(slug)
    if existing is not None:
        return existing, False
    row = await session.scalar(
        select(OrgQualitativeCharacteristic).where(
            OrgQualitativeCharacteristic.organization_id == organization_id,
            OrgQualitativeCharacteristic.slug == slug,
        )
    )
    if row is not None:
        char_by_slug[slug] = row
        return row, False
    row = OrgQualitativeCharacteristic(
        organization_id=organization_id,
        name=name,
        slug=slug,
        description=description,
        moscow=moscow,
        kind="placement",
    )
    session.add(row)
    await session.flush()
    char_by_slug[slug] = row
    return row, True


async def migrate_legacy_traits(
    session: AsyncSession,
    organization_id: str,
    *,
    actor_user_id: str,
) -> LegacyTraitsMigrateOut:
    """Copy legacy provider/region trait rows into qualitative characteristics + links."""
    char_by_slug: dict[str, OrgQualitativeCharacteristic] = {}
    for row in (
        await session.scalars(
            select(OrgQualitativeCharacteristic).where(
                OrgQualitativeCharacteristic.organization_id == organization_id
            )
        )
    ).all():
        char_by_slug[row.slug] = row

    characteristics_created = 0
    provider_links_added = 0
    region_links_added = 0

    provider_traits = (
        await session.scalars(
            select(ProviderTrait).where(ProviderTrait.organization_id == organization_id)
        )
    ).all()
    for trait in provider_traits:
        slug = trait.trait_key.strip().lower()[:64] or _slugify(trait.title)
        characteristic, created = await _get_or_create_characteristic_for_trait(
            session,
            organization_id,
            slug=slug,
            name=trait.title,
            description=trait.description,
            moscow=trait.moscow,
            char_by_slug=char_by_slug,
        )
        if created:
            characteristics_created += 1
        linked = await session.scalar(
            select(InfrastructureProviderCharacteristicLink.id).where(
                InfrastructureProviderCharacteristicLink.organization_id == organization_id,
                InfrastructureProviderCharacteristicLink.infrastructure_provider_id
                == trait.infrastructure_provider_id,
                InfrastructureProviderCharacteristicLink.characteristic_id == characteristic.id,
            )
        )
        if linked is None:
            session.add(
                InfrastructureProviderCharacteristicLink(
                    organization_id=organization_id,
                    infrastructure_provider_id=trait.infrastructure_provider_id,
                    characteristic_id=characteristic.id,
                )
            )
            provider_links_added += 1

    region_traits = (
        await session.scalars(
            select(RegionTrait).where(RegionTrait.organization_id == organization_id)
        )
    ).all()
    for trait in region_traits:
        slug = trait.trait_key.strip().lower()[:64] or _slugify(trait.title)
        characteristic, created = await _get_or_create_characteristic_for_trait(
            session,
            organization_id,
            slug=slug,
            name=trait.title,
            description=trait.description,
            moscow=trait.moscow,
            char_by_slug=char_by_slug,
        )
        if created:
            characteristics_created += 1
        linked = await session.scalar(
            select(RegionCharacteristicLink.id).where(
                RegionCharacteristicLink.organization_id == organization_id,
                RegionCharacteristicLink.region_id == trait.region_id,
                RegionCharacteristicLink.characteristic_id == characteristic.id,
            )
        )
        if linked is None:
            session.add(
                RegionCharacteristicLink(
                    organization_id=organization_id,
                    region_id=trait.region_id,
                    characteristic_id=characteristic.id,
                )
            )
            region_links_added += 1

    await audit.record_audit(
        session,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        action="characteristic.migrate_legacy_traits",
        entity_type="organization",
        entity_id=organization_id,
        detail=(
            f"provider_links={provider_links_added},region_links={region_links_added},"
            f"created={characteristics_created}"
        ),
    )
    return LegacyTraitsMigrateOut(
        provider_traits_seen=len(provider_traits),
        region_traits_seen=len(region_traits),
        characteristics_created=characteristics_created,
        provider_links_added=provider_links_added,
        region_links_added=region_links_added,
    )


async def region_characteristics_for_lineage(
    session: AsyncSession, organization_id: str, lineage_region_ids: list[str]
) -> list[tuple[str, OrgQualitativeCharacteristic]]:
    if not lineage_region_ids:
        return []
    result = await session.execute(
        select(RegionCharacteristicLink.region_id, OrgQualitativeCharacteristic)
        .join(
            OrgQualitativeCharacteristic,
            OrgQualitativeCharacteristic.id == RegionCharacteristicLink.characteristic_id,
        )
        .where(
            RegionCharacteristicLink.organization_id == organization_id,
            RegionCharacteristicLink.region_id.in_(lineage_region_ids),
        )
        .order_by(RegionCharacteristicLink.region_id)
    )
    return [(region_id, characteristic) for region_id, characteristic in result.all()]

