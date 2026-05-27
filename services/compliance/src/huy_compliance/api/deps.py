"""FastAPI dependencies."""

from __future__ import annotations

from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from huy_auth.auth_context import AuthContext
from huy_auth.jwt import decode_access_token
from huy_compliance.config import Settings, get_settings
from huy_compliance.db import get_db_session
from huy_compliance.services.projects_client import ProjectsClient
from huy_compliance.services.projects_client import ProjectsClient
from huy_compliance.services.registry_client import RegistryClient

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


async def get_bearer_token(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Security(_bearer)] = None,
) -> str:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Missing bearer token")
    return credentials.credentials


TokenDep = Annotated[str, Depends(get_bearer_token)]


def get_registry_client(settings: SettingsDep) -> RegistryClient:
    return RegistryClient(settings)


RegistryDep = Annotated[RegistryClient, Depends(get_registry_client)]


def get_projects_client(settings: SettingsDep) -> ProjectsClient:
    return ProjectsClient(settings)


ProjectsDep = Annotated[ProjectsClient, Depends(get_projects_client)]
