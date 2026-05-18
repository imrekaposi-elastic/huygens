"""Prometheus /metrics endpoint tests."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


def test_metrics_disabled(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        client.app.state.app_state.settings, "metrics_enabled", False
    )
    r = client.get("/metrics")
    assert r.status_code == 404


def test_metrics_exports_host_and_vm_series(client: TestClient) -> None:
    r = client.get("/metrics")
    assert r.status_code == 200
    assert "text/plain" in r.headers.get("content-type", "")
    body = r.text
    assert "huy_host_cpu_usage_percent" in body
    assert "huy_host_memory_total_bytes" in body
    assert "huy_host_disk_bytes" in body
    assert "huy_host_disk_read_bytes_total" in body
    assert "huy_libvirt_up" in body
    assert "huy_agent_info" in body


@patch("huy_libvirt_agent.services.prometheus_metrics.psutil.cpu_percent", return_value=42.5)
@patch("huy_libvirt_agent.services.prometheus_metrics.psutil.virtual_memory")
def test_metrics_cpu_value(
    mock_mem: MagicMock, _mock_cpu: MagicMock, client: TestClient
) -> None:
    mem = MagicMock(total=8_000_000_000, available=4_000_000_000, used=4_000_000_000, percent=50.0)
    mock_mem.return_value = mem
    r = client.get("/metrics")
    assert "huy_host_cpu_usage_percent 42.5" in r.text
    assert "huy_host_memory_total_bytes 8e+09" in r.text or "8000000000" in r.text
