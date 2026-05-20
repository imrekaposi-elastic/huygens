"""JSON host metrics snapshot for the console (complements Prometheus /metrics)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

import psutil

from huy_libvirt_agent.services.prometheus_metrics import _disk_mounts, _mountpoint_label

if TYPE_CHECKING:
    from huy_libvirt_agent.app_state import AppState


def _primary_disk(data_dir: str) -> dict | None:
    mounts = _disk_mounts(data_dir)
    primary = _mountpoint_label(data_dir)
    order = [primary, "/"] + [m for m in mounts if m not in (primary, "/")]
    for mount in order:
        try:
            usage = psutil.disk_usage(mount)
        except (OSError, PermissionError):
            continue
        return {
            "mount": mount,
            "total_bytes": int(usage.total),
            "used_bytes": int(usage.used),
            "free_bytes": int(usage.free),
            "usage_percent": float(usage.percent),
        }
    return None


def _vm_counts(state: AppState) -> tuple[int, int, dict[str, int]]:
    running = 0
    total = 0
    by_state: dict[str, int] = {}
    if state.libvirt is None:
        return 0, 0, by_state
    for name in state.libvirt.list_domains():
        total += 1
        try:
            _code, lv_state = state.libvirt.domain_state(name)
        except Exception:
            lv_state = "UNKNOWN"
        by_state[lv_state] = by_state.get(lv_state, 0) + 1
        if lv_state in ("RUNNING", "PAUSED", "PMSUSPENDED"):
            running += 1
    return running, total, by_state


def _memory_allocated_to_vms(state: AppState) -> int:
    allocated = 0
    if state.libvirt is None or not state.libvirt.connected:
        return 0
    for name in state.libvirt.list_domains():
        try:
            metrics = state.libvirt.domain_runtime_metrics(name)
            if metrics:
                allocated += int(metrics.get("memory_max_bytes") or 0)
        except Exception:
            continue
    return allocated


def collect_host_metrics_snapshot(state: AppState) -> dict:
    data_dir = str(state.settings.data_dir)
    mem = psutil.virtual_memory()
    running, total, by_state = _vm_counts(state)
    allocated_vm_mem = _memory_allocated_to_vms(state)

    disk_io: dict | None = None
    try:
        dio = psutil.disk_io_counters(perdisk=False)
        if dio:
            disk_io = {
                "read_bytes_total": int(dio.read_bytes),
                "write_bytes_total": int(dio.write_bytes),
                "read_ops_total": int(dio.read_count),
                "write_ops_total": int(dio.write_count),
            }
    except (OSError, AttributeError):
        pass

    network: dict | None = None
    try:
        nio = psutil.net_io_counters()
        if nio:
            network = {
                "bytes_sent_total": int(nio.bytes_sent),
                "bytes_recv_total": int(nio.bytes_recv),
            }
    except (OSError, AttributeError):
        pass

    return {
        "collected_at": datetime.now(UTC).isoformat(),
        "libvirt_connected": bool(state.libvirt and state.libvirt.connected),
        "vms": {
            "running": running,
            "total": total,
            "by_libvirt_state": by_state,
        },
        "cpu_percent": float(psutil.cpu_percent(interval=0.1)),
        "memory": {
            "total_bytes": int(mem.total),
            "used_bytes": int(mem.used),
            "available_bytes": int(mem.available),
            "usage_percent": float(mem.percent),
            "allocated_to_vms_bytes": allocated_vm_mem,
        },
        "disk": _primary_disk(data_dir),
        "disk_io": disk_io,
        "network": network,
    }
