"""Host metrics JSON endpoint."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_host_metrics_snapshot(client: TestClient, auth_headers: dict) -> None:
    response = client.get("/api/v1/agent/metrics", headers=auth_headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert "collected_at" in body
    assert "vms" in body
    assert "running" in body["vms"]
    assert "cpu_percent" in body
    assert body["memory"]["total_bytes"] > 0
    assert "disk" in body or body["disk"] is None
