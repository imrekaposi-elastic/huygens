from fastapi import APIRouter, HTTPException

from huy_registry.api.deps import PlatformAdminDep, SessionDep
from huy_registry.schemas import ProviderCreate, ProviderOut, RegionCreate, RegionOut
from huy_registry.services import provider_service

router = APIRouter(prefix="/api/v1/providers", tags=["providers"])


@router.post("", response_model=ProviderOut, status_code=201)
async def create_provider(
    body: ProviderCreate,
    _admin: PlatformAdminDep,
    session: SessionDep,
) -> ProviderOut:
    row = await provider_service.create_provider(session, body)
    return ProviderOut.model_validate(row)


@router.get("", response_model=list[ProviderOut])
async def list_providers(_admin: PlatformAdminDep, session: SessionDep) -> list[ProviderOut]:
    rows = await provider_service.list_providers(session)
    return [ProviderOut.model_validate(r) for r in rows]


@router.get("/{provider_id}", response_model=ProviderOut)
async def get_provider(
    provider_id: str,
    _admin: PlatformAdminDep,
    session: SessionDep,
) -> ProviderOut:
    row = await provider_service.get_provider(session, provider_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Provider not found")
    return ProviderOut.model_validate(row)


@router.post("/{provider_id}/regions", response_model=RegionOut, status_code=201)
async def create_region(
    provider_id: str,
    body: RegionCreate,
    _admin: PlatformAdminDep,
    session: SessionDep,
) -> RegionOut:
    row = await provider_service.create_region(session, provider_id, body)
    return RegionOut.model_validate(row)


@router.get("/{provider_id}/regions", response_model=list[RegionOut])
async def list_regions(
    provider_id: str,
    _admin: PlatformAdminDep,
    session: SessionDep,
) -> list[RegionOut]:
    if await provider_service.get_provider(session, provider_id) is None:
        raise HTTPException(status_code=404, detail="Provider not found")
    rows = await provider_service.list_regions(session, provider_id)
    return [RegionOut.model_validate(r) for r in rows]
