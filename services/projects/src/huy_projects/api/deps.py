"""FastAPI dependencies."""

from __future__ import annotations

from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from huy_auth.auth_context import AuthContext
from huy_auth.jwt import decode_access_token
from huy_projects.config import Settings, get_settings
from huy_projects.db import get_db_session
from huy_projects.models import Project
from huy_projects.services import project_service
from huy_projects.services.agent_proxy import AgentProxy
from huy_projects.services.authorization import require_project_read
from huy_projects.services.registry_client import RegistryClient

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


def get_registry_client(settings: SettingsDep) -> RegistryClient:
    return RegistryClient(settings)


RegistryClientDep = Annotated[RegistryClient, Depends(get_registry_client)]


def get_agent_proxy(registry: RegistryClientDep) -> AgentProxy:
    return AgentProxy(registry)


AgentProxyDep = Annotated[AgentProxy, Depends(get_agent_proxy)]


async def get_project_or_404(project_id: str, session: SessionDep) -> Project:
    project = await project_service.get_project(session, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


ProjectDep = Annotated[Project, Depends(get_project_or_404)]


async def get_readable_project(project: ProjectDep, user: CurrentUserDep) -> Project:
    require_project_read(user, project)
    return project


ReadableProjectDep = Annotated[Project, Depends(get_readable_project)]


async def get_bearer_token(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Security(_bearer)] = None,
) -> str:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Missing bearer token")
    return credentials.credentials


BearerTokenDep = Annotated[str, Depends(get_bearer_token)]
