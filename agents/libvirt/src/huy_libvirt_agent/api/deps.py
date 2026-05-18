"""FastAPI dependencies."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from huy_libvirt_agent.app_state import AppState

_bearer = HTTPBearer(auto_error=False)


def get_state(request: Request) -> AppState:
    return request.app.state.app_state


def verify_token(
    state: Annotated[AppState, Depends(get_state)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Security(_bearer)] = None,
) -> None:
    if credentials is None or credentials.credentials != state.settings.agent_token:
        raise HTTPException(status_code=401, detail="Invalid or missing bearer token")


def get_actor(x_actor: Annotated[str | None, Header(alias="X-Actor")] = None) -> str:
    return x_actor or "anonymous"


StateDep = Annotated[AppState, Depends(get_state)]
ActorDep = Annotated[str, Depends(get_actor)]
