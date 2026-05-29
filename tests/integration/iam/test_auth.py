"""IAM authentication and authorization against the running stack."""

from __future__ import annotations

import pytest

from http_client import ControlPlaneClient


@pytest.mark.integration
def test_login_rejects_invalid_credentials(cp: ControlPlaneClient) -> None:
    response = cp.web(
        "POST",
        "/api/v1/auth/login",
        auth=False,
        json={"username": cp.stack.username, "password": "wrong-password"},
    )
    assert response.status_code == 401


@pytest.mark.integration
def test_me_returns_platform_admin(cp: ControlPlaneClient) -> None:
    response = cp.iam("GET", "/api/v1/auth/me")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["username"] == cp.stack.username
    assert "platform_admin" in body.get("platform_roles", [])


@pytest.mark.integration
def test_protected_routes_require_bearer(cp: ControlPlaneClient) -> None:
    response = cp.iam("GET", "/api/v1/organizations", auth=False)
    assert response.status_code == 401
