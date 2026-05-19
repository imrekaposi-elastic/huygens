"""Keycloak OIDC login (Phase 2)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import RedirectResponse

from huy_iam.api.deps import SessionDep, SettingsDep
from huy_iam.schemas import OidcAuthorizeOut, TokenResponse
from huy_iam.security import create_access_token
from huy_iam.services import oidc_service

router = APIRouter(prefix="/api/v1/auth/oidc", tags=["auth-oidc"])


@router.get("/authorize", response_model=OidcAuthorizeOut)
async def oidc_authorize(
    session: SessionDep,
    settings: SettingsDep,
    organization_id: str = Query(..., description="Organization UUID for role mappings"),
) -> OidcAuthorizeOut:
    url = await oidc_service.start_login(session, settings, organization_id=organization_id)
    await session.commit()
    return OidcAuthorizeOut(authorization_url=url)


@router.get("/callback", response_model=TokenResponse)
async def oidc_callback(
    session: SessionDep,
    settings: SettingsDep,
    code: str = Query(...),
    state: str = Query(...),
    redirect: bool = Query(False, description="If true, redirect to OIDC_POST_LOGIN_REDIRECT with token"),
):
    ctx = await oidc_service.complete_login(session, settings, code=code, state=state)
    token = create_access_token(settings, ctx.to_jwt_claims())
    if redirect and settings.oidc_post_login_redirect:
        return RedirectResponse(
            url=f"{settings.oidc_post_login_redirect}?access_token={token}",
            status_code=302,
        )
    return TokenResponse(access_token=token, expires_in=settings.jwt_access_ttl_seconds)
