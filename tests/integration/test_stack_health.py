"""Verify the compose stack exposes healthy endpoints."""

from __future__ import annotations

import httpx
import pytest

from http_client import ControlPlaneClient
from settings import StackSettings


@pytest.mark.integration
def test_all_service_health_endpoints(stack_ready: StackSettings, http_client: httpx.Client) -> None:
    for name, url in stack_ready.service_health_urls().items():
        response = http_client.get(url)
        assert response.status_code == 200, f"{name} unhealthy at {url}: {response.text}"


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
