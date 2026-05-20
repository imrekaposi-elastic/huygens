"""Keycloak OIDC login (Phase 2)."""

from __future__ import annotations

from urllib.parse import quote

from fastapi import APIRouter, Query
from fastapi.responses import RedirectResponse

from huy_iam.api.deps import SessionDep, SettingsDep
from huy_iam.config import Settings
from huy_iam.schemas import OidcAuthorizeOut, TokenResponse
from huy_iam.security import create_access_token
from huy_iam.services import oidc_service

router = APIRouter(prefix="/api/v1/auth/oidc", tags=["auth-oidc"])


def build_spa_post_login_redirect_url(settings: Settings, access_token: str) -> str:
    """
    Redirect SPA after OIDC without putting JWT in the query string.

    Uses URL fragment (#) so tokens are not sent to server access logs (ADR 0011).
    Console reads hash on /auth/callback and stores token in memory — never ?access_token=.
    """
    base = (settings.oidc_post_login_redirect or "").rstrip("/")
    fragment = (
        f"access_token={quote(access_token, safe='')}"
        f"&token_type=Bearer"
        f"&expires_in={settings.jwt_access_ttl_seconds}"
    )
    return f"{base}#{fragment}"


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
    redirect: bool = Query(
        False,
        description="If true, redirect to OIDC_POST_LOGIN_REDIRECT with token in URL fragment (#), not query",
    ),
):
    ctx = await oidc_service.complete_login(session, settings, code=code, state=state)
    token = create_access_token(settings, ctx.to_jwt_claims())
    if redirect and settings.oidc_post_login_redirect:
        return RedirectResponse(
            url=build_spa_post_login_redirect_url(settings, token),
            status_code=302,
        )
    return TokenResponse(access_token=token, expires_in=settings.jwt_access_ttl_seconds)
