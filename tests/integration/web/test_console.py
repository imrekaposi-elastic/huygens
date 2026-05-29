"""Console nginx entrypoint against the running stack."""

from __future__ import annotations

import httpx
import pytest

from http_client import ControlPlaneClient


@pytest.mark.integration
def test_console_proxies_iam_login(cp: ControlPlaneClient) -> None:
    """Nginx on :5173 must route auth to IAM (console entrypoint)."""
    response = cp.web(
        "POST",
        "/api/v1/auth/login",
        auth=False,
        json={"username": cp.stack.username, "password": cp.stack.password},
    )
    assert response.status_code == 200, response.text
    assert "access_token" in response.json()


@pytest.mark.integration
def test_sse_via_console_nginx(cp: ControlPlaneClient, http_client: httpx.Client) -> None:
    with http_client.stream(
        "GET",
        f"{cp.stack.web_url}/api/v1/inventory/events/stream",
        headers={"Authorization": f"Bearer {cp.token}", "Accept": "text/event-stream"},
        timeout=10.0,
    ) as response:
        assert response.status_code == 200, response.text
        assert "text/event-stream" in response.headers.get("content-type", "")
