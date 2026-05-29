"""Verify the compose stack exposes healthy endpoints."""

from __future__ import annotations

import httpx
import pytest

from settings import StackSettings


@pytest.mark.integration
def test_all_service_health_endpoints(stack_ready: StackSettings, http_client: httpx.Client) -> None:
    for name, url in stack_ready.service_health_urls().items():
        response = http_client.get(url)
        assert response.status_code == 200, f"{name} unhealthy at {url}: {response.text}"
