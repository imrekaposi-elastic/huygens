"""Inventory dashboard and live SSE contract against the running stack."""

from __future__ import annotations

import httpx
import pytest

from http_client import ControlPlaneClient


@pytest.mark.integration
def test_inventory_dashboard_shape(cp: ControlPlaneClient, target_org_id: str) -> None:
    response = cp.inventory(
        "GET",
        f"/api/v1/inventory/organizations/{target_org_id}/dashboard",
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["organization_id"] == target_org_id
    assert "agent_count" in body
    assert "agents" in body
    assert isinstance(body["agents"], list)


@pytest.mark.integration
def test_sse_rejects_query_string_token(cp: ControlPlaneClient) -> None:
    response = cp.get(
        f"{cp.stack.inventory_url}/api/v1/inventory/events/stream?token=leaked",
        auth=False,
    )
    assert response.status_code == 400
    assert "query" in response.json()["detail"].lower()


@pytest.mark.integration
def test_sse_requires_bearer_header(cp: ControlPlaneClient) -> None:
    response = cp.get(
        f"{cp.stack.inventory_url}/api/v1/inventory/events/stream",
        auth=False,
    )
    assert response.status_code == 401


@pytest.mark.integration
def test_sse_accepts_bearer_and_emits_connected(
    cp: ControlPlaneClient,
    http_client: httpx.Client,
) -> None:
    with http_client.stream(
        "GET",
        f"{cp.stack.inventory_url}/api/v1/inventory/events/stream",
        headers={"Authorization": f"Bearer {cp.token}", "Accept": "text/event-stream"},
        timeout=10.0,
    ) as response:
        assert response.status_code == 200, response.text
        first_chunk = ""
        for chunk in response.iter_text():
            first_chunk += chunk
            if "connected" in first_chunk.lower():
                break
        assert "connected" in first_chunk.lower()


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
