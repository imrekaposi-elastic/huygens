"""Keycloak OIDC authorization code + PKCE (Phase 2)."""

from __future__ import annotations

import base64
import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlencode

import httpx
import structlog
from fastapi import HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from huy_iam.auth_context import AuthContext, OrgMembership
from huy_iam.config import Settings
from huy_iam.models import OidcLoginState, User
from huy_iam.services import idp_mapping_service, user_service

logger = structlog.get_logger(__name__)


def _pkce_pair() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).decode().rstrip("=")
    return verifier, challenge


def _issuer_base(settings: Settings) -> str:
    return settings.oidc_issuer.rstrip("/")


def build_authorize_url(settings: Settings, state: str, code_challenge: str) -> str:
    params = {
        "client_id": settings.oidc_client_id,
        "response_type": "code",
        "scope": settings.oidc_scopes,
        "redirect_uri": settings.oidc_redirect_uri,
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    return f"{_issuer_base(settings)}/protocol/openid-connect/auth?{urlencode(params)}"


async def start_login(
    session: AsyncSession,
    settings: Settings,
    *,
    organization_id: str,
) -> str:
    if not settings.oidc_enabled:
        raise HTTPException(status_code=503, detail="OIDC is not enabled")
    org = await user_service.get_organization(session, organization_id)
    if org is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    verifier, challenge = _pkce_pair()
    state = secrets.token_urlsafe(32)
    expires = datetime.now(UTC) + timedelta(minutes=10)
    session.add(
        OidcLoginState(
            state=state,
            code_verifier=verifier,
            organization_id=organization_id,
            expires_at=expires,
        )
    )
    await session.flush()
    return build_authorize_url(settings, state, challenge)


async def _consume_state(session: AsyncSession, state: str) -> OidcLoginState:
    result = await session.execute(select(OidcLoginState).where(OidcLoginState.state == state))
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=400, detail="Invalid or expired OIDC state")
    if datetime.now(UTC) >= row.expires_at:
        await session.execute(delete(OidcLoginState).where(OidcLoginState.state == state))
        raise HTTPException(status_code=400, detail="OIDC state expired")
    await session.execute(delete(OidcLoginState).where(OidcLoginState.state == state))
    return row


def _extract_groups(claims: dict[str, Any]) -> list[str]:
    groups = claims.get("groups")
    if isinstance(groups, list):
        return [str(g) for g in groups]
    if isinstance(groups, str):
        return [groups]
    realm = claims.get("realm_access") or {}
    if isinstance(realm, dict):
        roles = realm.get("roles")
        if isinstance(roles, list):
            return [str(r) for r in roles]
    return []


async def exchange_code(
    settings: Settings,
    *,
    code: str,
    code_verifier: str,
) -> dict[str, Any]:
    token_url = f"{_issuer_base(settings)}/protocol/openid-connect/token"
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": settings.oidc_redirect_uri,
        "client_id": settings.oidc_client_id,
        "code_verifier": code_verifier,
    }
    if settings.oidc_client_secret:
        data["client_secret"] = settings.oidc_client_secret
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(token_url, data=data)
        if response.status_code != 200:
            logger.warning("oidc_token_exchange_failed", status=response.status_code, body=response.text[:300])
            raise HTTPException(status_code=502, detail="OIDC token exchange failed")
        return response.json()


async def fetch_userinfo(settings: Settings, access_token: str) -> dict[str, Any]:
    url = f"{_issuer_base(settings)}/protocol/openid-connect/userinfo"
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(url, headers={"Authorization": f"Bearer {access_token}"})
        if response.status_code != 200:
            raise HTTPException(status_code=502, detail="OIDC userinfo failed")
        return response.json()


async def _upsert_oidc_user(
    session: AsyncSession,
    *,
    settings: Settings,
    claims: dict[str, Any],
) -> User:
    sub = str(claims.get("sub", ""))
    if not sub:
        raise HTTPException(status_code=502, detail="OIDC token missing sub")
    email = (claims.get("email") or f"{sub}@oidc.local").lower()
    username = (
        claims.get("preferred_username")
        or claims.get("username")
        or email.split("@")[0]
    )
    username = str(username)[:128]
    realm = settings.oidc_realm

    user = await user_service.get_user_by_external_subject(session, sub, realm)
    if user is None:
        user = await user_service.get_user_by_email(session, email)
    if user is None:
        user = await user_service.create_oidc_user(
            session,
            email=email,
            username=username,
            external_subject=sub,
            keycloak_realm=realm,
            display_name=claims.get("name"),
        )
    else:
        user.auth_provider = "oidc"
        user.external_subject = sub
        user.keycloak_realm = realm
        if claims.get("name"):
            user.display_name = str(claims["name"])
        user.is_active = True
        await session.flush()
    return user


async def complete_login(
    session: AsyncSession,
    settings: Settings,
    *,
    code: str,
    state: str,
) -> AuthContext:
    login_state = await _consume_state(session, state)
    token_payload = await exchange_code(
        settings, code=code, code_verifier=login_state.code_verifier
    )
    access_token = token_payload.get("access_token")
    if not access_token:
        raise HTTPException(status_code=502, detail="OIDC response missing access_token")
    userinfo = await fetch_userinfo(settings, str(access_token))
    user = await _upsert_oidc_user(session, settings=settings, claims=userinfo)
    groups = _extract_groups(userinfo)
    await idp_mapping_service.record_user_idp_groups(session, user.id, groups)
    ctx = await user_service.build_auth_context_with_idp(
        session,
        user,
        organization_id=login_state.organization_id,
        idp_groups=groups,
    )
    await session.commit()
    return ctx


async def build_auth_context_with_idp_for_user(
    session: AsyncSession,
    user: User,
    *,
    organization_id: str,
) -> AuthContext:
    groups = await idp_mapping_service.list_user_idp_groups(session, user.id)
    return await user_service.build_auth_context_with_idp(
        session, user, organization_id=organization_id, idp_groups=groups
    )
