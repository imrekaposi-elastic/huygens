"""Internal service-to-service auth."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, HTTPException

from huy_inventory.config import Settings, get_settings

SettingsDep = Annotated[Settings, Depends(get_settings)]


async def verify_internal_service(
    settings: SettingsDep,
    x_huy_service_token: Annotated[str | None, Header(alias="X-Huy-Service-Token")] = None,
) -> None:
    allowed = {settings.inventory_service_token, settings.ssh_gateway_service_token}
    if not x_huy_service_token or x_huy_service_token not in allowed:
        raise HTTPException(status_code=401, detail="Invalid service token")

InternalServiceDep = Annotated[None, Depends(verify_internal_service)]
