"""Infrastructure providers and hierarchical regions."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from huy_registry.api.deps import PlatformAdminDep, SessionDep
from huy_registry.schemas import (
    InfrastructureProviderCreate,
    InfrastructureProviderDetailOut,
    InfrastructureProviderOut,
    RegionCreate,
    RegionOut,
    RegionTreeNode,
)
from huy_registry.services import audit, infrastructure_service, region_tree_service

router = APIRouter(prefix="/api/v1/infrastructure-providers", tags=["infrastructure-providers"])


@router.post("", response_model=InfrastructureProviderOut, status_code=201)
async def create_infrastructure_provider(
    body: InfrastructureProviderCreate,
    admin: PlatformAdminDep,
    session: SessionDep,
) -> InfrastructureProviderOut:
    row = await infrastructure_service.create_infrastructure_provider(session, body)
    await audit.record_platform_audit(
        actor_user_id=admin.user_id,
        action="infrastructure_provider.create",
        resource_type="infrastructure_provider",
        resource_id=row.id,
        message=row.slug,
    )
    return InfrastructureProviderOut.model_validate(row)


@router.get("", response_model=list[InfrastructureProviderOut])
async def list_infrastructure_providers(
    _admin: PlatformAdminDep,
    session: SessionDep,
) -> list[InfrastructureProviderOut]:
    providers = await infrastructure_service.list_infrastructure_providers(session)
    out: list[InfrastructureProviderOut] = []
    for provider in providers:
        pair = await region_tree_service.get_provider_with_tree(session, provider.id)
        if pair is None:
            continue
        summary, _ = pair
        out.append(summary)
    return out


@router.get("/{infrastructure_provider_id}", response_model=InfrastructureProviderDetailOut)
async def get_infrastructure_provider(
    infrastructure_provider_id: str,
    _admin: PlatformAdminDep,
    session: SessionDep,
) -> InfrastructureProviderDetailOut:
    pair = await region_tree_service.get_provider_with_tree(session, infrastructure_provider_id)
    if pair is None:
        raise HTTPException(status_code=404, detail="Infrastructure provider not found")
    summary, forest = pair
    return InfrastructureProviderDetailOut(**summary.model_dump(), region_tree=forest)


@router.delete("/{infrastructure_provider_id}", status_code=204)
async def delete_infrastructure_provider(
    infrastructure_provider_id: str,
    _admin: PlatformAdminDep,
    session: SessionDep,
) -> None:
    deleted = await infrastructure_service.delete_infrastructure_provider(
        session, infrastructure_provider_id
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Infrastructure provider not found")
    await audit.record_platform_audit(
        actor_user_id=_admin.user_id,
        action="infrastructure_provider.delete",
        resource_type="infrastructure_provider",
        resource_id=infrastructure_provider_id,
    )


@router.post("/{infrastructure_provider_id}/regions", response_model=RegionOut, status_code=201)
async def create_region(
    infrastructure_provider_id: str,
    body: RegionCreate,
    admin: PlatformAdminDep,
    session: SessionDep,
) -> RegionOut:
    row = await infrastructure_service.create_region(session, infrastructure_provider_id, body)
    await audit.record_platform_audit(
        actor_user_id=admin.user_id,
        action="infrastructure_region.create",
        resource_type="infrastructure_region",
        resource_id=row.id,
        message=row.slug,
        labels={"infrastructure_provider_id": infrastructure_provider_id},
    )
    return RegionOut.model_validate(row)


@router.get("/{infrastructure_provider_id}/regions", response_model=list[RegionOut])
async def list_root_regions(
    infrastructure_provider_id: str,
    _admin: PlatformAdminDep,
    session: SessionDep,
) -> list[RegionOut]:
    if await infrastructure_service.get_infrastructure_provider(session, infrastructure_provider_id) is None:
        raise HTTPException(status_code=404, detail="Infrastructure provider not found")
    rows = await infrastructure_service.list_root_regions(session, infrastructure_provider_id)
    return [RegionOut.model_validate(r) for r in rows]


@router.get(
    "/{infrastructure_provider_id}/region-tree",
    response_model=list[RegionTreeNode],
)
async def get_region_tree(
    infrastructure_provider_id: str,
    _admin: PlatformAdminDep,
    session: SessionDep,
) -> list[RegionTreeNode]:
    pair = await region_tree_service.get_provider_with_tree(session, infrastructure_provider_id)
    if pair is None:
        raise HTTPException(status_code=404, detail="Infrastructure provider not found")
    _, forest = pair
    return forest


@router.delete("/{infrastructure_provider_id}/regions/{region_id}", status_code=204)
async def delete_region(
    infrastructure_provider_id: str,
    region_id: str,
    _admin: PlatformAdminDep,
    session: SessionDep,
) -> None:
    deleted = await infrastructure_service.delete_region(
        session, infrastructure_provider_id, region_id
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Region not found")
    await audit.record_platform_audit(
        actor_user_id=_admin.user_id,
        action="infrastructure_region.delete",
        resource_type="infrastructure_region",
        resource_id=region_id,
        labels={"infrastructure_provider_id": infrastructure_provider_id},
    )
