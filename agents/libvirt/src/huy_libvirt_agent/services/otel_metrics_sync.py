"""Export hypervisor Prometheus samples to OpenTelemetry gauges (OTLP)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from opentelemetry import metrics

from huy_libvirt_agent.services.prometheus_metrics import (
    HuyMetricsCollector,
    _collect_host,
    _collect_libvirt,
)

if TYPE_CHECKING:
    from huy_libvirt_agent.app_state import AppState

_gauges: dict[str, Any] = {}


def _gauge(meter: metrics.Meter, name: str) -> Any:
    if name not in _gauges:
        _gauges[name] = meter.create_gauge(
            name,
            description=f"Huygens hypervisor metric {name}",
        )
    return _gauges[name]


def _record_family(meter: metrics.Meter, family: Any) -> None:
    for sample in family.samples:
        labels = dict(sample.labels) if sample.labels else {}
        gauge = _gauge(meter, sample.name)
        if labels:
            gauge.set(float(sample.value), attributes=labels)
        else:
            gauge.set(float(sample.value))


def sync_hypervisor_metrics_to_otel(state: AppState) -> None:
    """Push current host/VM/libvirt samples to the OTel meter (scraped by OTLP reader)."""
    meter = metrics.get_meter("huy_libvirt_agent.hypervisor")
    data_dir = str(state.settings.data_dir)
    for family in _collect_host(data_dir):
        _record_family(meter, family)
    for family in _collect_libvirt(state):
        _record_family(meter, family)
    collector = HuyMetricsCollector()
    for family in collector.collect():
        if family.name == "huy_agent_info":
            _record_family(meter, family)
