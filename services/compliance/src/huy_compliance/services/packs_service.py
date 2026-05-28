"""Compliance packs import/list (Phase 7+)."""

from __future__ import annotations

import re

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from huy_compliance.models import OrgComplianceControl, OrgCompliancePack, OrgComplianceStandard
from huy_compliance.schemas import CompliancePackImportIn, CompliancePackOut, CompliancePackValidateOut
from huy_compliance.services import audit


def _pack_out(row: OrgCompliancePack) -> CompliancePackOut:
    return CompliancePackOut(
        id=row.id,
        organization_id=row.organization_id,
        pack_key=row.pack_key,
        name=row.name,
        vendor=row.vendor,
        version=row.version,
        imported_by=row.imported_by,
        imported_at=row.imported_at,
    )


async def list_packs(session: AsyncSession, organization_id: str) -> list[CompliancePackOut]:
    rows = (
        await session.scalars(
            select(OrgCompliancePack)
            .where(OrgCompliancePack.organization_id == organization_id)
            .order_by(OrgCompliancePack.imported_at.desc())
        )
    ).all()
    return [_pack_out(r) for r in rows]


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-")
    return slug[:64] or "standard"


async def validate_pack(
    session: AsyncSession,
    organization_id: str,
    body: CompliancePackImportIn,
) -> CompliancePackValidateOut:
    errors: list[str] = []
    standards_to_create = 0
    controls_to_create = 0

    existing_pack = await session.scalar(
        select(OrgCompliancePack).where(
            OrgCompliancePack.organization_id == organization_id,
            OrgCompliancePack.pack_key == body.pack_key,
        )
    )
    if existing_pack:
        errors.append(f"Pack '{body.pack_key}' already imported")

    payload = body.payload or {}
    standards = payload.get("standards") if isinstance(payload, dict) else None
    if standards is not None and not isinstance(standards, list):
        errors.append("pack payload 'standards' must be a list")
        standards = []

    if isinstance(standards, list):
        for s in standards:
            if not isinstance(s, dict):
                errors.append("pack payload standard must be an object")
                continue
            s_name = (s.get("name") or "").strip()
            if not s_name:
                errors.append("pack standard missing 'name'")
                continue
            s_slug = (s.get("slug") or _slugify(s_name)).strip()
            existing_std = await session.scalar(
                select(OrgComplianceStandard).where(
                    OrgComplianceStandard.organization_id == organization_id,
                    OrgComplianceStandard.slug == s_slug,
                )
            )
            if existing_std:
                errors.append(f"Standard slug '{s_slug}' already exists")
                continue
            standards_to_create += 1
            controls = s.get("controls", [])
            if controls is None:
                controls = []
            if not isinstance(controls, list):
                errors.append(f"standard '{s_slug}' controls must be a list")
                continue
            for c in controls:
                if not isinstance(c, dict):
                    errors.append(f"standard '{s_slug}' control must be an object")
                    continue
                c_name = (c.get("name") or "").strip()
                if not c_name:
                    errors.append(f"standard '{s_slug}' control missing 'name'")
                    continue
                controls_to_create += 1

    return CompliancePackValidateOut(
        pack_key=body.pack_key,
        name=body.name,
        vendor=body.vendor,
        version=body.version,
        standards_to_create=standards_to_create,
        controls_to_create=controls_to_create,
        errors=errors,
    )


async def import_pack(
    session: AsyncSession,
    organization_id: str,
    body: CompliancePackImportIn,
    *,
    actor_user_id: str,
) -> CompliancePackOut:
    validation = await validate_pack(session, organization_id, body)
    if validation.errors:
        raise HTTPException(status_code=400, detail="; ".join(validation.errors[:5]))

    existing = await session.scalar(
        select(OrgCompliancePack).where(
            OrgCompliancePack.organization_id == organization_id,
            OrgCompliancePack.pack_key == body.pack_key,
        )
    )
    if existing:
        raise HTTPException(status_code=409, detail=f"Pack '{body.pack_key}' already imported")
    row = OrgCompliancePack(
        organization_id=organization_id,
        pack_key=body.pack_key,
        name=body.name,
        vendor=body.vendor,
        version=body.version,
        raw_json=body.payload,
        imported_by=actor_user_id,
    )
    session.add(row)
    await session.flush()

    # Increment 4: apply pack payload after passing dry-run validation.
    payload = body.payload or {}
    standards = payload.get("standards") if isinstance(payload, dict) else None
    if standards is not None and not isinstance(standards, list):
        raise HTTPException(status_code=400, detail="pack payload 'standards' must be a list")

    if isinstance(standards, list) and standards:
        for s in standards:
            if not isinstance(s, dict):
                raise HTTPException(status_code=400, detail="pack payload standard must be an object")
            s_name = (s.get("name") or "").strip()
            if not s_name:
                raise HTTPException(status_code=400, detail="pack standard missing 'name'")
            s_slug = (s.get("slug") or _slugify(s_name)).strip()
            existing_std = await session.scalar(
                select(OrgComplianceStandard).where(
                    OrgComplianceStandard.organization_id == organization_id,
                    OrgComplianceStandard.slug == s_slug,
                )
            )
            if existing_std:
                raise HTTPException(
                    status_code=409,
                    detail=f"Standard slug '{s_slug}' already exists; cannot apply pack",
                )
            std = OrgComplianceStandard(
                organization_id=organization_id,
                name=s_name,
                slug=s_slug,
                description=s.get("description"),
                reference_url=s.get("reference_url"),
                moscow=(s.get("moscow") or "should"),
                target_level=s.get("target_level"),
            )
            session.add(std)
            await session.flush()

            controls = s.get("controls", [])
            if controls is None:
                controls = []
            if not isinstance(controls, list):
                raise HTTPException(status_code=400, detail=f"standard '{s_slug}' controls must be a list")
            for c in controls:
                if not isinstance(c, dict):
                    raise HTTPException(status_code=400, detail=f"standard '{s_slug}' control must be an object")
                c_name = (c.get("name") or "").strip()
                if not c_name:
                    raise HTTPException(status_code=400, detail=f"standard '{s_slug}' control missing 'name'")
                ctrl = OrgComplianceControl(
                    organization_id=organization_id,
                    standard_id=std.id,
                    control_code=c.get("control_code"),
                    name=c_name,
                    description=c.get("description"),
                    rationale=c.get("rationale"),
                    moscow=(c.get("moscow") or "should"),
                )
                session.add(ctrl)

    await audit.record_audit(
        session,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        action="pack.import",
        entity_type="compliance_pack",
        entity_id=row.id,
        detail=row.pack_key,
    )
    return _pack_out(row)

