"""Authentication routes."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, HTTPException

from huy_iam.api.converters import user_to_out
from huy_iam.api.deps import CurrentUserDep, SessionDep, SettingsDep
from huy_iam.models import ApiKey
from huy_iam.schemas import ApiKeyCreate, ApiKeyCreated, LoginRequest, TokenResponse, UserOut
from huy_iam.security import create_access_token, generate_api_key_material
from huy_iam.services import user_service

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, session: SessionDep, settings: SettingsDep) -> TokenResponse:
    user = await user_service.authenticate_password(session, body.username, body.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    ctx = await user_service.build_auth_context(session, user)
    token = create_access_token(settings, ctx.to_jwt_claims())
    return TokenResponse(access_token=token, expires_in=settings.jwt_access_ttl_seconds)


@router.get("/me", response_model=UserOut)
async def me(user: CurrentUserDep, session: SessionDep) -> UserOut:
    db_user = await user_service.get_user_by_id(session, user.user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    ctx = await user_service.build_auth_context(session, db_user)
    return user_to_out(ctx, db_user)


@router.post("/api-keys", response_model=ApiKeyCreated, status_code=201)
async def create_api_key(
    body: ApiKeyCreate,
    user: CurrentUserDep,
    session: SessionDep,
) -> ApiKeyCreated:
    full_key, prefix, key_hash = generate_api_key_material()
    expires_at = None
    if body.expires_in_days is not None:
        expires_at = datetime.now(UTC) + timedelta(days=body.expires_in_days)
    row = ApiKey(
        user_id=user.user_id,
        name=body.name,
        key_prefix=prefix,
        key_hash=key_hash,
        expires_at=expires_at,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return ApiKeyCreated(
        id=row.id,
        name=row.name,
        key_prefix=row.key_prefix,
        api_key=full_key,
        expires_at=row.expires_at,
    )
