"""GRC primitives: standards, controls, cycles (Phase 7+)."""

from __future__ import annotations

import re

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from huy_compliance.models import OrgComplianceControl, OrgComplianceCycle, OrgComplianceStandard, utc_now
from huy_compliance.schemas import (
    ComplianceControlCreate,
    ComplianceControlOut,
    ComplianceControlUpdate,
    ComplianceCycleCreate,
    ComplianceCycleOut,
    ComplianceCycleUpdate,
    ComplianceStandardCreate,
    ComplianceStandardOut,
    ComplianceStandardUpdate,
)
from huy_compliance.services import audit


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug[:64] or "standard"


def _standard_out(row: OrgComplianceStandard) -> ComplianceStandardOut:
    return ComplianceStandardOut(
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


def _control_out(row: OrgComplianceControl) -> ComplianceControlOut:
    return ComplianceControlOut(
        id=row.id,
        organization_id=row.organization_id,
        standard_id=row.standard_id,
        control_code=row.control_code,
        name=row.name,
        description=row.description,
        rationale=row.rationale,
        moscow=row.moscow,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _cycle_out(row: OrgComplianceCycle) -> ComplianceCycleOut:
    return ComplianceCycleOut(
        id=row.id,
        organization_id=row.organization_id,
        standard_id=row.standard_id,
        name=row.name,
        status=row.status,
        starts_at=row.starts_at,
        ends_at=row.ends_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


async def list_standards(session: AsyncSession, organization_id: str) -> list[ComplianceStandardOut]:
    rows = (
        await session.scalars(
            select(OrgComplianceStandard)
            .where(OrgComplianceStandard.organization_id == organization_id)
            .order_by(OrgComplianceStandard.name)
        )
    ).all()
    return [_standard_out(r) for r in rows]


async def create_standard(
    session: AsyncSession,
    organization_id: str,
    body: ComplianceStandardCreate,
    *,
    actor_user_id: str,
) -> ComplianceStandardOut:
    slug = body.slug or _slugify(body.name)
    existing = await session.scalar(
        select(OrgComplianceStandard).where(
            OrgComplianceStandard.organization_id == organization_id,
            OrgComplianceStandard.slug == slug,
        )
    )
    if existing:
        raise HTTPException(status_code=409, detail=f"Standard slug '{slug}' already exists")
    row = OrgComplianceStandard(
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
        action="standard.create",
        entity_type="compliance_standard",
        entity_id=row.id,
        detail=row.name,
    )
    return _standard_out(row)


async def update_standard(
    session: AsyncSession,
    organization_id: str,
    standard_id: str,
    body: ComplianceStandardUpdate,
    *,
    actor_user_id: str,
) -> ComplianceStandardOut:
    row = await session.get(OrgComplianceStandard, standard_id)
    if row is None or row.organization_id != organization_id:
        raise HTTPException(status_code=404, detail="Compliance standard not found")
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
        action="standard.update",
        entity_type="compliance_standard",
        entity_id=row.id,
    )
    return _standard_out(row)


async def delete_standard(
    session: AsyncSession,
    organization_id: str,
    standard_id: str,
    *,
    actor_user_id: str,
) -> None:
    row = await session.get(OrgComplianceStandard, standard_id)
    if row is None or row.organization_id != organization_id:
        raise HTTPException(status_code=404, detail="Compliance standard not found")
    await session.delete(row)
    await audit.record_audit(
        session,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        action="standard.delete",
        entity_type="compliance_standard",
        entity_id=standard_id,
    )


async def list_controls(
    session: AsyncSession, organization_id: str, standard_id: str
) -> list[ComplianceControlOut]:
    rows = (
        await session.scalars(
            select(OrgComplianceControl)
            .where(
                OrgComplianceControl.organization_id == organization_id,
                OrgComplianceControl.standard_id == standard_id,
            )
            .order_by(OrgComplianceControl.control_code, OrgComplianceControl.name)
        )
    ).all()
    return [_control_out(r) for r in rows]


async def create_control(
    session: AsyncSession,
    organization_id: str,
    standard_id: str,
    body: ComplianceControlCreate,
    *,
    actor_user_id: str,
) -> ComplianceControlOut:
    standard = await session.get(OrgComplianceStandard, standard_id)
    if standard is None or standard.organization_id != organization_id:
        raise HTTPException(status_code=404, detail="Compliance standard not found")
    row = OrgComplianceControl(
        organization_id=organization_id,
        standard_id=standard_id,
        control_code=body.control_code,
        name=body.name,
        description=body.description,
        rationale=body.rationale,
        moscow=body.moscow,
    )
    session.add(row)
    await session.flush()
    await audit.record_audit(
        session,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        action="control.create",
        entity_type="compliance_control",
        entity_id=row.id,
        detail=row.name,
    )
    return _control_out(row)


async def update_control(
    session: AsyncSession,
    organization_id: str,
    control_id: str,
    body: ComplianceControlUpdate,
    *,
    actor_user_id: str,
) -> ComplianceControlOut:
    row = await session.get(OrgComplianceControl, control_id)
    if row is None or row.organization_id != organization_id:
        raise HTTPException(status_code=404, detail="Compliance control not found")
    if body.control_code is not None:
        row.control_code = body.control_code
    if body.name is not None:
        row.name = body.name
    if body.description is not None:
        row.description = body.description
    if body.rationale is not None:
        row.rationale = body.rationale
    if body.moscow is not None:
        row.moscow = body.moscow
    row.updated_at = utc_now()
    await audit.record_audit(
        session,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        action="control.update",
        entity_type="compliance_control",
        entity_id=row.id,
    )
    return _control_out(row)


async def delete_control(
    session: AsyncSession,
    organization_id: str,
    control_id: str,
    *,
    actor_user_id: str,
) -> None:
    row = await session.get(OrgComplianceControl, control_id)
    if row is None or row.organization_id != organization_id:
        raise HTTPException(status_code=404, detail="Compliance control not found")
    await session.delete(row)
    await audit.record_audit(
        session,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        action="control.delete",
        entity_type="compliance_control",
        entity_id=control_id,
    )


async def list_cycles(
    session: AsyncSession, organization_id: str, standard_id: str
) -> list[ComplianceCycleOut]:
    rows = (
        await session.scalars(
            select(OrgComplianceCycle)
            .where(
                OrgComplianceCycle.organization_id == organization_id,
                OrgComplianceCycle.standard_id == standard_id,
            )
            .order_by(OrgComplianceCycle.created_at.desc())
        )
    ).all()
    return [_cycle_out(r) for r in rows]


async def create_cycle(
    session: AsyncSession,
    organization_id: str,
    standard_id: str,
    body: ComplianceCycleCreate,
    *,
    actor_user_id: str,
) -> ComplianceCycleOut:
    standard = await session.get(OrgComplianceStandard, standard_id)
    if standard is None or standard.organization_id != organization_id:
        raise HTTPException(status_code=404, detail="Compliance standard not found")
    row = OrgComplianceCycle(
        organization_id=organization_id,
        standard_id=standard_id,
        name=body.name,
        status=body.status,
        starts_at=body.starts_at,
        ends_at=body.ends_at,
    )
    session.add(row)
    await session.flush()
    await audit.record_audit(
        session,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        action="cycle.create",
        entity_type="compliance_cycle",
        entity_id=row.id,
        detail=row.name,
    )
    return _cycle_out(row)


async def update_cycle(
    session: AsyncSession,
    organization_id: str,
    cycle_id: str,
    body: ComplianceCycleUpdate,
    *,
    actor_user_id: str,
) -> ComplianceCycleOut:
    row = await session.get(OrgComplianceCycle, cycle_id)
    if row is None or row.organization_id != organization_id:
        raise HTTPException(status_code=404, detail="Compliance cycle not found")
    if body.name is not None:
        row.name = body.name
    if body.status is not None:
        row.status = body.status
    if body.starts_at is not None:
        row.starts_at = body.starts_at
    if body.ends_at is not None:
        row.ends_at = body.ends_at
    row.updated_at = utc_now()
    await audit.record_audit(
        session,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        action="cycle.update",
        entity_type="compliance_cycle",
        entity_id=row.id,
    )
    return _cycle_out(row)


async def delete_cycle(
    session: AsyncSession,
    organization_id: str,
    cycle_id: str,
    *,
    actor_user_id: str,
) -> None:
    row = await session.get(OrgComplianceCycle, cycle_id)
    if row is None or row.organization_id != organization_id:
        raise HTTPException(status_code=404, detail="Compliance cycle not found")
    await session.delete(row)
    await audit.record_audit(
        session,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        action="cycle.delete",
        entity_type="compliance_cycle",
        entity_id=cycle_id,
    )

