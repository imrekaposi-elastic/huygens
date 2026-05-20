"""OIDC console redirect must not leak JWT in query strings."""

from __future__ import annotations

from huy_iam.api.routes.oidc import build_spa_post_login_redirect_url
from huy_iam.config import Settings


def test_spa_post_login_redirect_uses_fragment_not_query() -> None:
    settings = Settings(
        OIDC_POST_LOGIN_REDIRECT="http://localhost:5173/auth/callback",
        JWT_ACCESS_TTL_SECONDS=3600,
    )
    url = build_spa_post_login_redirect_url(settings, "eyJhbGciOiJIUzI1NiJ9.test")
    assert "?" not in url.split("#", 1)[0]
    assert "#access_token=" in url
    assert "token_type=Bearer" in url
    assert "expires_in=3600" in url
    assert "access_token=eyJhbGciOiJIUzI1NiJ9.test" in url
