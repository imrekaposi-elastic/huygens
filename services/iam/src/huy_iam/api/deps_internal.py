"""Internal service-to-service auth (ssh-gateway, agents)."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, HTTPException

from huy_iam.config import Settings, get_settings

SettingsDep = Annotated[Settings, Depends(get_settings)]


def _internal_tokens(settings: Settings) -> frozenset[str]:
    return frozenset({settings.iam_service_token, settings.ssh_gateway_service_token})


async def verify_internal_service(
    settings: SettingsDep,
    x_huy_service_token: Annotated[str | None, Header(alias="X-Huy-Service-Token")] = None,
) -> None:
    if x_huy_service_token not in _internal_tokens(settings):
        raise HTTPException(status_code=401, detail="Invalid service token")


InternalServiceDep = Annotated[None, Depends(verify_internal_service)]
