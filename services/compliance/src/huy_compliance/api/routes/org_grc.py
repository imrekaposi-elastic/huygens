"""Org-scoped GRC APIs (Phase 7+)."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Form, Query, UploadFile
from fastapi.responses import FileResponse
from fastapi.responses import Response

from huy_compliance.api.deps import CurrentUserDep, SessionDep, SettingsDep
from huy_compliance.schemas import (
    CharacteristicLinkSet,
    ComplianceControlCreate,
    ComplianceControlOut,
    ComplianceControlUpdate,
    ComplianceCycleCreate,
    ComplianceCycleOut,
    ComplianceCycleStatusOut,
    ComplianceCycleUpdate,
    ControlEvidenceOut,
    ComplianceExportJobOut,
    ComplianceExportRequest,
    CompliancePackImportIn,
    CompliancePackOut,
    CompliancePackValidateOut,
    ComplianceStandardCreate,
    ComplianceStandardOut,
    ComplianceStandardUpdate,
    LegacyTraitsMigrateOut,
    QualitativeCharacteristicCreate,
    QualitativeCharacteristicOut,
    QualitativeCharacteristicUpdate,
)
from huy_compliance.services import (
    authorization,
    characteristics_service,
    cycle_status_service,
    evidence_service,
    export_service,
    grc_service,
    packs_service,
)

router = APIRouter(prefix="/api/v1/organizations/{organization_id}", tags=["grc"])


@router.get("/compliance-standards", response_model=list[ComplianceStandardOut])
async def list_standards(
    organization_id: str,
    user: CurrentUserDep,
    session: SessionDep,
) -> list[ComplianceStandardOut]:
    authorization.require_compliance_read(user, organization_id)
    return await grc_service.list_standards(session, organization_id)


@router.post("/compliance-standards", response_model=ComplianceStandardOut, status_code=201)
async def create_standard(
    organization_id: str,
    body: ComplianceStandardCreate,
    user: CurrentUserDep,
    session: SessionDep,
) -> ComplianceStandardOut:
    authorization.require_catalog_manage(user, organization_id)
    row = await grc_service.create_standard(
        session, organization_id, body, actor_user_id=user.user_id
    )
    await session.commit()
    return row


@router.patch("/compliance-standards/{standard_id}", response_model=ComplianceStandardOut)
async def update_standard(
    organization_id: str,
    standard_id: str,
    body: ComplianceStandardUpdate,
    user: CurrentUserDep,
    session: SessionDep,
) -> ComplianceStandardOut:
    authorization.require_catalog_manage(user, organization_id)
    row = await grc_service.update_standard(
        session, organization_id, standard_id, body, actor_user_id=user.user_id
    )
    await session.commit()
    return row


@router.delete("/compliance-standards/{standard_id}", status_code=204)
async def delete_standard(
    organization_id: str,
    standard_id: str,
    user: CurrentUserDep,
    session: SessionDep,
    settings: SettingsDep,
) -> None:
    authorization.require_catalog_manage(user, organization_id)
    # Ensure object-store evidence isn't left behind (DB will cascade delete rows).
    await evidence_service.delete_all_evidence_for_standard(
        session, settings, organization_id, standard_id, actor_user_id=user.user_id
    )
    await grc_service.delete_standard(
        session, organization_id, standard_id, actor_user_id=user.user_id
    )
    await session.commit()


@router.get(
    "/compliance-standards/{standard_id}/controls",
    response_model=list[ComplianceControlOut],
)
async def list_controls(
    organization_id: str,
    standard_id: str,
    user: CurrentUserDep,
    session: SessionDep,
) -> list[ComplianceControlOut]:
    authorization.require_compliance_read(user, organization_id)
    return await grc_service.list_controls(session, organization_id, standard_id)


@router.post(
    "/compliance-standards/{standard_id}/controls",
    response_model=ComplianceControlOut,
    status_code=201,
)
async def create_control(
    organization_id: str,
    standard_id: str,
    body: ComplianceControlCreate,
    user: CurrentUserDep,
    session: SessionDep,
) -> ComplianceControlOut:
    authorization.require_catalog_manage(user, organization_id)
    row = await grc_service.create_control(
        session, organization_id, standard_id, body, actor_user_id=user.user_id
    )
    await session.commit()
    return row


@router.patch("/compliance-controls/{control_id}", response_model=ComplianceControlOut)
async def update_control(
    organization_id: str,
    control_id: str,
    body: ComplianceControlUpdate,
    user: CurrentUserDep,
    session: SessionDep,
) -> ComplianceControlOut:
    authorization.require_catalog_manage(user, organization_id)
    row = await grc_service.update_control(
        session, organization_id, control_id, body, actor_user_id=user.user_id
    )
    await session.commit()
    return row


@router.delete("/compliance-controls/{control_id}", status_code=204)
async def delete_control(
    organization_id: str,
    control_id: str,
    user: CurrentUserDep,
    session: SessionDep,
    settings: SettingsDep,
) -> None:
    authorization.require_catalog_manage(user, organization_id)
    # Ensure object-store evidence isn't left behind (DB will cascade delete rows).
    await evidence_service.delete_all_evidence_for_control(
        session, settings, organization_id, control_id, actor_user_id=user.user_id
    )
    await grc_service.delete_control(
        session, organization_id, control_id, actor_user_id=user.user_id
    )
    await session.commit()


@router.get(
    "/compliance-standards/{standard_id}/cycles",
    response_model=list[ComplianceCycleOut],
)
async def list_cycles(
    organization_id: str,
    standard_id: str,
    user: CurrentUserDep,
    session: SessionDep,
) -> list[ComplianceCycleOut]:
    authorization.require_compliance_read(user, organization_id)
    return await grc_service.list_cycles(session, organization_id, standard_id)


@router.post(
    "/compliance-standards/{standard_id}/cycles",
    response_model=ComplianceCycleOut,
    status_code=201,
)
async def create_cycle(
    organization_id: str,
    standard_id: str,
    body: ComplianceCycleCreate,
    user: CurrentUserDep,
    session: SessionDep,
) -> ComplianceCycleOut:
    authorization.require_catalog_manage(user, organization_id)
    row = await grc_service.create_cycle(
        session, organization_id, standard_id, body, actor_user_id=user.user_id
    )
    await session.commit()
    return row


@router.patch("/compliance-cycles/{cycle_id}", response_model=ComplianceCycleOut)
async def update_cycle(
    organization_id: str,
    cycle_id: str,
    body: ComplianceCycleUpdate,
    user: CurrentUserDep,
    session: SessionDep,
) -> ComplianceCycleOut:
    authorization.require_catalog_manage(user, organization_id)
    row = await grc_service.update_cycle(
        session, organization_id, cycle_id, body, actor_user_id=user.user_id
    )
    await session.commit()
    return row


@router.delete("/compliance-cycles/{cycle_id}", status_code=204)
async def delete_cycle(
    organization_id: str,
    cycle_id: str,
    user: CurrentUserDep,
    session: SessionDep,
) -> None:
    authorization.require_catalog_manage(user, organization_id)
    await grc_service.delete_cycle(
        session, organization_id, cycle_id, actor_user_id=user.user_id
    )
    await session.commit()


@router.get("/compliance-cycles/{cycle_id}/status", response_model=ComplianceCycleStatusOut)
async def cycle_status(
    organization_id: str,
    cycle_id: str,
    user: CurrentUserDep,
    session: SessionDep,
) -> ComplianceCycleStatusOut:
    authorization.require_compliance_read(user, organization_id)
    return await cycle_status_service.cycle_status(session, organization_id, cycle_id)


@router.get("/compliance-packs", response_model=list[CompliancePackOut])
async def list_packs(
    organization_id: str,
    user: CurrentUserDep,
    session: SessionDep,
) -> list[CompliancePackOut]:
    authorization.require_compliance_read(user, organization_id)
    return await packs_service.list_packs(session, organization_id)


@router.post("/compliance-packs/import", response_model=CompliancePackOut, status_code=201)
async def import_pack(
    organization_id: str,
    body: CompliancePackImportIn,
    user: CurrentUserDep,
    session: SessionDep,
) -> CompliancePackOut:
    authorization.require_catalog_manage(user, organization_id)
    row = await packs_service.import_pack(
        session, organization_id, body, actor_user_id=user.user_id
    )
    await session.commit()
    return row


@router.post("/compliance-packs/validate", response_model=CompliancePackValidateOut)
async def validate_pack(
    organization_id: str,
    body: CompliancePackImportIn,
    user: CurrentUserDep,
    session: SessionDep,
) -> CompliancePackValidateOut:
    authorization.require_catalog_manage(user, organization_id)
    return await packs_service.validate_pack(session, organization_id, body)


@router.post("/compliance-export", response_model=ComplianceExportJobOut, status_code=201)
async def request_export(
    organization_id: str,
    body: ComplianceExportRequest,
    user: CurrentUserDep,
    session: SessionDep,
    settings: SettingsDep,
) -> ComplianceExportJobOut:
    authorization.require_catalog_manage(user, organization_id)
    row = await export_service.request_export(
        session,
        settings,
        organization_id,
        body,
        actor_user_id=user.user_id,
        actor_display_name=export_service.format_user_display_name(
            username=user.username,
            email=user.email,
            user_id=user.user_id,
        ),
    )
    await session.commit()
    # Best-effort async processing in-process (sufficient for dev/MVP).
    # Use create_task to properly run the async coroutine.
    asyncio.create_task(
        export_service.run_export_job_detached(
            settings,
            organization_id,
            row.id,
            actor_user_id=user.user_id,
        )
    )
    return row


@router.get("/compliance-export/{job_id}", response_model=ComplianceExportJobOut)
async def get_export(
    organization_id: str,
    job_id: str,
    user: CurrentUserDep,
    session: SessionDep,
) -> ComplianceExportJobOut:
    authorization.require_compliance_read(user, organization_id)
    return await export_service.get_export_job(session, organization_id, job_id)


@router.get("/compliance-export/{job_id}/download")
async def download_export(
    organization_id: str,
    job_id: str,
    user: CurrentUserDep,
    session: SessionDep,
    settings: SettingsDep,
) -> Response:
    authorization.require_compliance_read(user, organization_id)
    data, filename = await export_service.download_export(session, settings, organization_id, job_id)
    await session.commit()
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return Response(content=data, media_type="application/pdf", headers=headers)


@router.get("/qualitative-characteristics", response_model=list[QualitativeCharacteristicOut])
async def list_characteristics(
    organization_id: str,
    user: CurrentUserDep,
    session: SessionDep,
) -> list[QualitativeCharacteristicOut]:
    authorization.require_compliance_read(user, organization_id)
    return await characteristics_service.list_characteristics(session, organization_id)


@router.post(
    "/qualitative-characteristics/migrate-from-legacy-traits",
    response_model=LegacyTraitsMigrateOut,
)
async def migrate_legacy_traits(
    organization_id: str,
    user: CurrentUserDep,
    session: SessionDep,
) -> LegacyTraitsMigrateOut:
    authorization.require_catalog_manage(user, organization_id)
    result = await characteristics_service.migrate_legacy_traits(
        session, organization_id, actor_user_id=user.user_id
    )
    await session.commit()
    return result


@router.post("/qualitative-characteristics", response_model=QualitativeCharacteristicOut, status_code=201)
async def create_characteristic(
    organization_id: str,
    body: QualitativeCharacteristicCreate,
    user: CurrentUserDep,
    session: SessionDep,
) -> QualitativeCharacteristicOut:
    authorization.require_catalog_manage(user, organization_id)
    row = await characteristics_service.create_characteristic(
        session, organization_id, body, actor_user_id=user.user_id
    )
    await session.commit()
    return row


@router.patch(
    "/qualitative-characteristics/{characteristic_id}",
    response_model=QualitativeCharacteristicOut,
)
async def update_characteristic(
    organization_id: str,
    characteristic_id: str,
    body: QualitativeCharacteristicUpdate,
    user: CurrentUserDep,
    session: SessionDep,
) -> QualitativeCharacteristicOut:
    authorization.require_catalog_manage(user, organization_id)
    row = await characteristics_service.update_characteristic(
        session, organization_id, characteristic_id, body, actor_user_id=user.user_id
    )
    await session.commit()
    return row


@router.delete("/qualitative-characteristics/{characteristic_id}", status_code=204)
async def delete_characteristic(
    organization_id: str,
    characteristic_id: str,
    user: CurrentUserDep,
    session: SessionDep,
) -> None:
    authorization.require_catalog_manage(user, organization_id)
    await characteristics_service.delete_characteristic(
        session, organization_id, characteristic_id, actor_user_id=user.user_id
    )
    await session.commit()


@router.put("/infrastructure-providers/{provider_id}/characteristics", status_code=204)
async def set_provider_characteristics(
    organization_id: str,
    provider_id: str,
    body: CharacteristicLinkSet,
    user: CurrentUserDep,
    session: SessionDep,
) -> None:
    authorization.require_catalog_manage(user, organization_id)
    await characteristics_service.set_provider_characteristics(
        session, organization_id, provider_id, body, actor_user_id=user.user_id
    )
    await session.commit()


@router.get(
    "/infrastructure-providers/{provider_id}/characteristics",
    response_model=CharacteristicLinkSet,
)
async def get_provider_characteristics(
    organization_id: str,
    provider_id: str,
    user: CurrentUserDep,
    session: SessionDep,
) -> CharacteristicLinkSet:
    authorization.require_compliance_read(user, organization_id)
    ids = await characteristics_service.get_provider_characteristic_ids(
        session, organization_id, provider_id
    )
    return CharacteristicLinkSet(characteristic_ids=ids)


@router.put("/regions/{region_id}/characteristics", status_code=204)
async def set_region_characteristics(
    organization_id: str,
    region_id: str,
    body: CharacteristicLinkSet,
    user: CurrentUserDep,
    session: SessionDep,
) -> None:
    authorization.require_catalog_manage(user, organization_id)
    await characteristics_service.set_region_characteristics(
        session, organization_id, region_id, body, actor_user_id=user.user_id
    )
    await session.commit()


@router.get("/regions/{region_id}/characteristics", response_model=CharacteristicLinkSet)
async def get_region_characteristics(
    organization_id: str,
    region_id: str,
    user: CurrentUserDep,
    session: SessionDep,
) -> CharacteristicLinkSet:
    authorization.require_compliance_read(user, organization_id)
    ids = await characteristics_service.get_region_characteristic_ids(session, organization_id, region_id)
    return CharacteristicLinkSet(characteristic_ids=ids)


@router.get(
    "/compliance-controls/{control_id}/evidence",
    response_model=list[ControlEvidenceOut],
)
async def list_control_evidence(
    organization_id: str,
    control_id: str,
    user: CurrentUserDep,
    session: SessionDep,
    cycle_id: str | None = Query(default=None),
    include_superseded: bool = Query(default=False),
) -> list[ControlEvidenceOut]:
    authorization.require_compliance_read(user, organization_id)
    return await evidence_service.list_evidence(
        session,
        organization_id,
        control_id,
        cycle_id=cycle_id,
        include_superseded=include_superseded,
    )


@router.post(
    "/compliance-controls/{control_id}/evidence",
    response_model=ControlEvidenceOut,
    status_code=201,
)
async def upload_control_evidence(
    organization_id: str,
    control_id: str,
    user: CurrentUserDep,
    session: SessionDep,
    settings: SettingsDep,
    file: UploadFile,
    category: str = Form(...),
    title: str = Form(...),
    summary: str | None = Form(default=None),
    cycle_id: str | None = Form(default=None),
    supersedes_evidence_id: str | None = Form(default=None),
) -> ControlEvidenceOut:
    authorization.require_catalog_manage(user, organization_id)
    row = await evidence_service.upload_evidence(
        session,
        settings,
        organization_id,
        control_id,
        cycle_id=cycle_id,
        category=category,
        title=title,
        summary=summary,
        tags=None,
        file=file,
        actor_user_id=user.user_id,
        supersedes_evidence_id=supersedes_evidence_id,
    )
    await session.commit()
    return row


@router.get("/compliance-evidence/{evidence_id}/download")
async def download_evidence(
    organization_id: str,
    evidence_id: str,
    user: CurrentUserDep,
    session: SessionDep,
    settings: SettingsDep,
) -> FileResponse:
    authorization.require_compliance_read(user, organization_id)
    return await evidence_service.download_evidence(session, settings, organization_id, evidence_id)


@router.delete("/compliance-evidence/{evidence_id}", status_code=204)
async def delete_evidence(
    organization_id: str,
    evidence_id: str,
    user: CurrentUserDep,
    session: SessionDep,
    settings: SettingsDep,
) -> None:
    authorization.require_catalog_manage(user, organization_id)
    await evidence_service.delete_evidence(
        session,
        settings,
        organization_id,
        evidence_id,
        actor_user_id=user.user_id,
    )
    await session.commit()

