"""Cycle readiness / coverage computation (Increment 2)."""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from huy_compliance.models import OrgComplianceControl, OrgComplianceCycle, OrgControlEvidence
from huy_compliance.schemas import ComplianceCycleStatusOut
from huy_compliance.services import catalog_service


async def cycle_status(
    session: AsyncSession,
    organization_id: str,
    cycle_id: str,
) -> ComplianceCycleStatusOut:
    cycle = await session.get(OrgComplianceCycle, cycle_id)
    if cycle is None or cycle.organization_id != organization_id:
        raise HTTPException(status_code=404, detail="Compliance cycle not found")

    controls_total = int(
        await session.scalar(
            select(func.count())
            .select_from(OrgComplianceControl)
            .where(
                OrgComplianceControl.organization_id == organization_id,
                OrgComplianceControl.standard_id == cycle.standard_id,
            )
        )
        or 0
    )

    # Evidence counts by category for this cycle
    ev_rows = (
        await session.execute(
            select(OrgControlEvidence.control_id, OrgControlEvidence.category, func.count())
            .where(
                OrgControlEvidence.organization_id == organization_id,
                OrgControlEvidence.cycle_id == cycle_id,
            )
            .group_by(OrgControlEvidence.control_id, OrgControlEvidence.category)
        )
    ).all()

    evidence_by_category: dict[str, int] = {}
    control_has_any: set[str] = set()
    control_has_cat: dict[str, set[str]] = {}
    for control_id, category, count in ev_rows:
        control_has_any.add(control_id)
        evidence_by_category[str(category)] = evidence_by_category.get(str(category), 0) + int(count)
        control_has_cat.setdefault(str(category), set()).add(control_id)

    categories = ["design", "implementation", "operating"]
    missing_by_cat: dict[str, int] = {}
    for cat in categories:
        missing_by_cat[cat] = max(0, controls_total - len(control_has_cat.get(cat, set())))

    dash = await catalog_service.dashboard(session, organization_id)

    return ComplianceCycleStatusOut(
        organization_id=organization_id,
        cycle_id=cycle.id,
        standard_id=cycle.standard_id,
        cycle_name=cycle.name,
        cycle_status=cycle.status,
        controls_total=controls_total,
        controls_with_any_evidence=len(control_has_any),
        evidence_by_category=evidence_by_category,
        missing_evidence_controls_by_category=missing_by_cat,
        checks_active=dash.checks_active,
        checks_expiring_soon=dash.checks_expiring_soon,
        checks_expired=dash.checks_expired,
    )

