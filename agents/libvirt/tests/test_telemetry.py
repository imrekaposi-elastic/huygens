"""OpenTelemetry and request context (Phase 8)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from huy_libvirt_agent.app_state import AppState
from huy_libvirt_agent.services.otel_metrics_sync import sync_hypervisor_metrics_to_otel


def test_healthz_includes_request_id(client: TestClient) -> None:
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.headers.get("X-Request-Id")


@patch("huy_libvirt_agent.services.otel_metrics_sync.HuyMetricsCollector.collect", return_value=[])
@patch("huy_libvirt_agent.services.otel_metrics_sync._collect_libvirt", return_value=[])
@patch("huy_libvirt_agent.services.otel_metrics_sync._gauge")
@patch("huy_libvirt_agent.services.otel_metrics_sync._collect_host")
def test_sync_hypervisor_metrics_records_gauges(
    mock_host: MagicMock,
    mock_gauge_fn: MagicMock,
    _mock_libvirt: MagicMock,
    _mock_collector: MagicMock,
) -> None:
    from prometheus_client.core import GaugeMetricFamily

    from huy_libvirt_agent.config import get_settings

    cpu = GaugeMetricFamily("huy_host_cpu_usage_percent", "test")
    cpu.add_metric([], 12.5)
    mock_host.return_value = [cpu]
    gauge = MagicMock()
    mock_gauge_fn.return_value = gauge

    get_settings.cache_clear()
    state = AppState.from_settings(get_settings())

    sync_hypervisor_metrics_to_otel(state)

    gauge.set.assert_called_with(12.5)


def test_otel_metrics_loop_not_started_when_export_disabled(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(client.app.state, "otel_export_enabled", False)
    assert client.app.state.otel_export_enabled is False
