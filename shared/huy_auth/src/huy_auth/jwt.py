"""Decode IAM access tokens."""

from __future__ import annotations

import jwt


def decode_access_token(
    token: str,
    *,
    secret: str,
    issuer: str,
) -> dict:
    return jwt.decode(
        token,
        secret,
        algorithms=["HS256"],
        issuer=issuer,
        options={"require": ["exp", "iat", "sub"]},
    )
