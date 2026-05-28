"""Evidence upload/list/download (Phase 7+)."""

from __future__ import annotations

import hashlib

from fastapi import HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from huy_compliance.config import Settings
from huy_compliance.models import OrgComplianceControl, OrgComplianceCycle, OrgControlEvidence
from huy_compliance.schemas import ControlEvidenceOut
from huy_compliance.services import audit
from huy_compliance.services.object_store import ObjectStore


def _evidence_out(row: OrgControlEvidence) -> ControlEvidenceOut:
    return ControlEvidenceOut(
        id=row.id,
        organization_id=row.organization_id,
        control_id=row.control_id,
        cycle_id=row.cycle_id,
        category=row.category,
        title=row.title,
        summary=row.summary,
        file_name=row.file_name,
        content_type=row.content_type,
        size_bytes=row.size_bytes,
        sha256=row.sha256,
        tags=row.tags or {},
        uploaded_by=row.uploaded_by,
        uploaded_at=row.uploaded_at,
        supersedes_evidence_id=row.supersedes_evidence_id,
    )


async def list_evidence(
    session: AsyncSession,
    organization_id: str,
    control_id: str,
    *,
    cycle_id: str | None = None,
    include_superseded: bool = False,
) -> list[ControlEvidenceOut]:
    # Superseded evidence is inferred from the forward-pointer `supersedes_evidence_id`.
    # Any evidence whose id appears as another row's `supersedes_evidence_id` is considered superseded.
    superseded_ids_subq = (
        select(OrgControlEvidence.supersedes_evidence_id)
        .where(
            OrgControlEvidence.organization_id == organization_id,
            OrgControlEvidence.control_id == control_id,
            OrgControlEvidence.supersedes_evidence_id.is_not(None),
        )
        .subquery()
    )

    q = select(OrgControlEvidence).where(
        OrgControlEvidence.organization_id == organization_id,
        OrgControlEvidence.control_id == control_id,
    )
    if cycle_id is not None:
        q = q.where(OrgControlEvidence.cycle_id == cycle_id)
    if not include_superseded:
        q = q.where(OrgControlEvidence.id.not_in(select(superseded_ids_subq.c.supersedes_evidence_id)))
    rows = (await session.scalars(q.order_by(OrgControlEvidence.uploaded_at.desc()))).all()
    return [_evidence_out(r) for r in rows]


async def upload_evidence(
    session: AsyncSession,
    settings: Settings,
    organization_id: str,
    control_id: str,
    *,
    cycle_id: str | None,
    category: str,
    title: str,
    summary: str | None,
    tags: dict | None,
    file: UploadFile,
    actor_user_id: str,
    supersedes_evidence_id: str | None = None,
) -> ControlEvidenceOut:
    control = await session.get(OrgComplianceControl, control_id)
    if control is None or control.organization_id != organization_id:
        raise HTTPException(status_code=404, detail="Compliance control not found")
    if cycle_id is not None:
        cycle = await session.get(OrgComplianceCycle, cycle_id)
        if cycle is None or cycle.organization_id != organization_id:
            raise HTTPException(status_code=400, detail="Unknown cycle_id")
    if supersedes_evidence_id is not None:
        prev = await session.get(OrgControlEvidence, supersedes_evidence_id)
        if prev is None or prev.organization_id != organization_id or prev.control_id != control_id:
            raise HTTPException(status_code=400, detail="Unknown supersedes_evidence_id")

    content = await file.read()
    digest = hashlib.sha256(content).hexdigest()

    row = OrgControlEvidence(
        organization_id=organization_id,
        control_id=control_id,
        cycle_id=cycle_id,
        category=category,
        title=title,
        summary=summary,
        file_name=file.filename,
        content_type=file.content_type,
        sha256=digest,
        size_bytes=len(content),
        uploaded_by=actor_user_id,
        supersedes_evidence_id=supersedes_evidence_id,
        tags=tags or {},
        object_key="",
    )
    session.add(row)
    await session.flush()

    prefix = settings.object_store_prefix.strip("/") if settings.object_store_prefix else "huy-compliance"
    safe_name = (file.filename or "evidence.bin").replace("/", "_")
    key = f"{prefix}/orgs/{organization_id}/evidence/{row.id}/{safe_name}"
    store = ObjectStore(settings)
    store.put_bytes(key=key, data=content)
    row.object_key = key

    await audit.record_audit(
        session,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        action="evidence.upload",
        entity_type="control_evidence",
        entity_id=row.id,
        detail=title,
    )
    if supersedes_evidence_id is not None:
        await audit.record_audit(
            session,
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            action="evidence.supersede",
            entity_type="control_evidence",
            entity_id=row.id,
            detail=supersedes_evidence_id,
        )
    return _evidence_out(row)


async def download_evidence(
    session: AsyncSession,
    settings: Settings,
    organization_id: str,
    evidence_id: str,
) -> FileResponse | StreamingResponse:
    row = await session.get(OrgControlEvidence, evidence_id)
    if row is None or row.organization_id != organization_id:
        raise HTTPException(status_code=404, detail="Evidence not found")
    store = ObjectStore(settings)
    if settings.object_store_kind == "s3":
        stream, length = store.stream_bytes(key=row.object_key)
        media_type = row.content_type or "application/octet-stream"
        filename = row.file_name or "evidence.bin"
        headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
        if length is not None:
            headers["Content-Length"] = str(length)
        return StreamingResponse(stream, media_type=media_type, headers=headers)
    path = store.get_path(key=row.object_key)
    filename = row.file_name or path.name
    media_type = row.content_type or "application/octet-stream"
    return FileResponse(path, filename=filename, media_type=media_type)


async def delete_evidence(
    session: AsyncSession,
    settings: Settings,
    organization_id: str,
    evidence_id: str,
    *,
    actor_user_id: str,
) -> None:
    row = await session.get(OrgControlEvidence, evidence_id)
    if row is None or row.organization_id != organization_id:
        raise HTTPException(status_code=404, detail="Evidence not found")
    store = ObjectStore(settings)
    store.delete(key=row.object_key)
    await session.delete(row)
    await audit.record_audit(
        session,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        action="evidence.delete",
        entity_type="control_evidence",
        entity_id=evidence_id,
        detail=row.title,
    )


async def delete_all_evidence_for_control(
    session: AsyncSession,
    settings: Settings,
    organization_id: str,
    control_id: str,
    *,
    actor_user_id: str,
) -> int:
    """Best-effort cleanup of object-store objects before the DB cascade delete."""
    q = select(OrgControlEvidence).where(
        OrgControlEvidence.organization_id == organization_id,
        OrgControlEvidence.control_id == control_id,
    )
    rows = (await session.scalars(q)).all()
    store = ObjectStore(settings)
    for r in rows:
        store.delete(key=r.object_key)
        await audit.record_audit(
            session,
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            action="evidence.delete",
            entity_type="control_evidence",
            entity_id=r.id,
            detail=r.title,
        )
    # DB rows will be removed by FK cascade when the control is deleted.
    return len(rows)


async def delete_all_evidence_for_standard(
    session: AsyncSession,
    settings: Settings,
    organization_id: str,
    standard_id: str,
    *,
    actor_user_id: str,
) -> int:
    """Cleanup evidence objects for all controls under a standard."""
    controls = (
        await session.scalars(
            select(OrgComplianceControl.id).where(
                OrgComplianceControl.organization_id == organization_id,
                OrgComplianceControl.standard_id == standard_id,
            )
        )
    ).all()
    total = 0
    for cid in controls:
        total += await delete_all_evidence_for_control(
            session, settings, organization_id, cid, actor_user_id=actor_user_id
        )
    return total

