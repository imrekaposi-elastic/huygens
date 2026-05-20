"""Internal service-to-service auth."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, HTTPException

from huy_projects.api.deps import SessionDep
from huy_projects.config import Settings, get_settings

SettingsDep = Annotated[Settings, Depends(get_settings)]


def _internal_service_tokens(settings: Settings) -> frozenset[str]:
    tokens = {settings.projects_service_token}
    if settings.inventory_service_token:
        tokens.add(settings.inventory_service_token)
    return frozenset(tokens)


async def verify_internal_service(
    settings: SettingsDep,
    x_huy_service_token: Annotated[str | None, Header(alias="X-Huy-Service-Token")] = None,
) -> None:
    if x_huy_service_token not in _internal_service_tokens(settings):
        raise HTTPException(status_code=401, detail="Invalid service token")


InternalServiceDep = Annotated[None, Depends(verify_internal_service)]
