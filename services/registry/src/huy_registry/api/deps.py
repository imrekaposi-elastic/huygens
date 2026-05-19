"""FastAPI dependencies."""

from __future__ import annotations

from typing import Annotated

import jwt
from fastapi import Depends, Header, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from huy_auth.auth_context import AuthContext
from huy_auth.jwt import decode_access_token
from huy_auth.roles import PERM_AGENT_EXPORT_TOKEN, PERM_AGENT_REGISTER, PERM_INVENTORY_READ
from huy_registry.config import Settings, get_settings
from huy_registry.db import get_db_session

_bearer = HTTPBearer(auto_error=False)

SettingsDep = Annotated[Settings, Depends(get_settings)]
SessionDep = Annotated[AsyncSession, Depends(get_db_session)]


async def get_current_user(
    settings: SettingsDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Security(_bearer)] = None,
) -> AuthContext:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Missing bearer token")
    try:
        claims = decode_access_token(
            credentials.credentials,
            secret=settings.jwt_secret,
            issuer=settings.jwt_issuer,
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid bearer token") from exc
    return AuthContext.from_jwt_claims(claims)


CurrentUserDep = Annotated[AuthContext, Depends(get_current_user)]


def require_platform_admin():
    async def _check(user: CurrentUserDep) -> AuthContext:
        if not user.is_platform_admin():
            raise HTTPException(status_code=403, detail="platform_admin required")
        return user

    return _check


PlatformAdminDep = Annotated[AuthContext, Depends(require_platform_admin())]


def require_permission(permission: str):
    async def _check(user: CurrentUserDep) -> AuthContext:
        if not user.has_permission(permission):
            raise HTTPException(status_code=403, detail=f"Permission denied: {permission}")
        return user

    return _check


AgentRegisterDep = Annotated[AuthContext, Depends(require_permission(PERM_AGENT_REGISTER))]
AgentExportDep = Annotated[AuthContext, Depends(require_permission(PERM_AGENT_EXPORT_TOKEN))]
InventoryReadDep = Annotated[AuthContext, Depends(require_permission(PERM_INVENTORY_READ))]


async def verify_inventory_service(
    settings: SettingsDep,
    x_huy_service_token: Annotated[str | None, Header(alias="X-Huy-Service-Token")] = None,
) -> None:
    if x_huy_service_token != settings.inventory_service_token:
        raise HTTPException(status_code=401, detail="Invalid service token")


InventoryServiceDep = Annotated[None, Depends(verify_inventory_service)]
