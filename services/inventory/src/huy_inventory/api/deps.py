"""FastAPI dependencies."""

from __future__ import annotations

from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from huy_auth.auth_context import AuthContext
from huy_auth.jwt import decode_access_token
from huy_auth.roles import PERM_INVENTORY_READ
from huy_inventory.config import Settings, get_settings
from huy_inventory.db import get_db_session

_bearer = HTTPBearer(auto_error=False)

# JWT in query strings is forbidden (EventSource ?token= anti-pattern).
_FORBIDDEN_QUERY_AUTH_PARAMS = frozenset({"token", "access_token", "jwt", "bearer"})

SettingsDep = Annotated[Settings, Depends(get_settings)]
SessionDep = Annotated[AsyncSession, Depends(get_db_session)]


async def reject_query_token_auth(request: Request) -> None:
    """Block ?token= and similar — use Authorization: Bearer only."""
    for key in request.query_params:
        if key.lower() in _FORBIDDEN_QUERY_AUTH_PARAMS:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Do not pass JWT in query parameters. "
                    "Use Authorization: Bearer header (fetch-based SSE, not EventSource ?token=)."
                ),
            )


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


def require_inventory_read():
    async def _check(user: CurrentUserDep) -> AuthContext:
        if not user.has_permission(PERM_INVENTORY_READ):
            raise HTTPException(status_code=403, detail="Permission denied")
        return user

    return _check


InventoryReadDep = Annotated[AuthContext, Depends(require_inventory_read())]
