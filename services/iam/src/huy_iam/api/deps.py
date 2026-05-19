"""FastAPI dependencies for auth and RBAC."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from huy_iam.auth_context import AuthContext
from huy_iam.config import Settings, get_settings
from huy_iam.db import get_db_session
from huy_iam.security import API_KEY_PREFIX, decode_access_token
from huy_iam.services import user_service

_bearer = HTTPBearer(auto_error=False)


async def get_session() -> AsyncSession:
    async for session in get_db_session():
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


async def get_current_user(
    session: SessionDep,
    settings: SettingsDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Security(_bearer)] = None,
) -> AuthContext:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = credentials.credentials
    if token.startswith(API_KEY_PREFIX):
        user = await user_service.authenticate_api_key(session, token)
        if user is None:
            raise HTTPException(status_code=401, detail="Invalid API key")
        return await user_service.build_auth_context(session, user)
    try:
        claims = decode_access_token(settings, token)
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from exc
    return AuthContext.from_jwt_claims(claims)


CurrentUserDep = Annotated[AuthContext, Depends(get_current_user)]


def require_platform_admin():
    async def _check(user: CurrentUserDep) -> AuthContext:
        if not user.is_platform_admin():
            raise HTTPException(status_code=403, detail="platform_admin required")
        return user

    return _check


def require_permission(permission: str, organization_id_param: str | None = None):
    async def _check(user: CurrentUserDep) -> AuthContext:
        org_id = organization_id_param
        if not user.has_permission(permission, org_id):
            raise HTTPException(status_code=403, detail=f"Permission denied: {permission}")
        return user

    return _check


PlatformAdminDep = Annotated[AuthContext, Depends(require_platform_admin())]
