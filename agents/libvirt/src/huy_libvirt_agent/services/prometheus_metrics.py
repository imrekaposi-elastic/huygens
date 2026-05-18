"""Prometheus metrics collection for host and VM resources."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import psutil
import structlog
from prometheus_client.core import GaugeMetricFamily
from prometheus_client.registry import REGISTRY

if TYPE_CHECKING:
    from huy_libvirt_agent.app_state import AppState

logger = structlog.get_logger(__name__)

_COLLECTOR_REGISTERED = False


def _mountpoint_label(path: str) -> str:
    return path.replace("\\", "/").rstrip("/") or "/"


def _disk_mounts(data_dir: str) -> list[str]:
    mounts = {"/", _mountpoint_label(data_dir)}
    try:
        for part in psutil.disk_partitions(all=False):
            if part.mountpoint in ("/", "/var", "/home"):
                mounts.add(_mountpoint_label(part.mountpoint))
    except (OSError, PermissionError):
        pass
    return sorted(mounts)


def _collect_host(data_dir: str) -> list[GaugeMetricFamily]:
    families: list[GaugeMetricFamily] = []

    cpu = GaugeMetricFamily(
        "huy_host_cpu_usage_percent",
        "Host CPU utilization (all cores, 100% = fully utilized)",
    )
    cpu.add_metric([], psutil.cpu_percent(interval=0.1))
    families.append(cpu)

    for name, idx in (("1m", 0), ("5m", 1), ("15m", 2)):
        load = GaugeMetricFamily(
            f"huy_host_load_{name}",
            f"Host load average ({name})",
        )
        try:
            load.add_metric([], os.getloadavg()[idx])
        except OSError:
            load.add_metric([], 0.0)
        families.append(load)

    mem = psutil.virtual_memory()
    for metric_name, value, help_text in (
        (
            "huy_host_memory_total_bytes",
            float(mem.total),
            "Total physical memory on the hypervisor",
        ),
        (
            "huy_host_memory_available_bytes",
            float(mem.available),
            "Available memory (including reclaimable cache)",
        ),
        (
            "huy_host_memory_used_bytes",
            float(mem.used),
            "Used memory excluding cache",
        ),
        (
            "huy_host_memory_usage_percent",
            float(mem.percent),
            "Memory use as a percentage of total",
        ),
    ):
        fam = GaugeMetricFamily(metric_name, help_text)
        fam.add_metric([], value)
        families.append(fam)

    disk_usage = GaugeMetricFamily(
        "huy_host_disk_bytes",
        "Disk space on the hypervisor",
        labels=["mount", "kind"],
    )
    disk_used_pct = GaugeMetricFamily(
        "huy_host_disk_usage_percent",
        "Disk use as a percentage of total",
        labels=["mount"],
    )
    for mount in _disk_mounts(data_dir):
        try:
            usage = psutil.disk_usage(mount)
        except (OSError, PermissionError):
            continue
        disk_usage.add_metric([mount, "total"], float(usage.total))
        disk_usage.add_metric([mount, "used"], float(usage.used))
        disk_usage.add_metric([mount, "free"], float(usage.free))
        disk_used_pct.add_metric([mount], float(usage.percent))
    families.extend([disk_usage, disk_used_pct])

    try:
        dio = psutil.disk_io_counters(perdisk=False)
        if dio:
            for metric_name, value, help_text in (
                (
                    "huy_host_disk_read_bytes_total",
                    float(dio.read_bytes),
                    "Cumulative bytes read from block devices",
                ),
                (
                    "huy_host_disk_write_bytes_total",
                    float(dio.write_bytes),
                    "Cumulative bytes written to block devices",
                ),
                (
                    "huy_host_disk_read_operations_total",
                    float(dio.read_count),
                    "Cumulative disk read operations",
                ),
                (
                    "huy_host_disk_write_operations_total",
                    float(dio.write_count),
                    "Cumulative disk write operations",
                ),
            ):
                fam = GaugeMetricFamily(metric_name, help_text)
                fam.add_metric([], value)
                families.append(fam)
    except (OSError, AttributeError):
        pass

    return families


def _collect_libvirt(state: AppState) -> list[GaugeMetricFamily]:
    families: list[GaugeMetricFamily] = []

    up = GaugeMetricFamily(
        "huy_libvirt_up",
        "Whether the agent is connected to libvirt (1=up)",
    )
    up.add_metric([], 1.0 if state.libvirt.connected else 0.0)
    families.append(up)

    vm_count = GaugeMetricFamily(
        "huy_vms",
        "Number of libvirt domains",
        labels=["libvirt_state"],
    )
    vm_vcpu = GaugeMetricFamily(
        "huy_vm_vcpu_count",
        "Configured vCPUs for the domain",
        labels=["vm"],
    )
    vm_mem_max = GaugeMetricFamily(
        "huy_vm_memory_max_bytes",
        "Maximum memory configured for the domain (bytes)",
        labels=["vm"],
    )
    vm_mem_used = GaugeMetricFamily(
        "huy_vm_memory_used_bytes",
        "Memory in use by the running domain (bytes, from libvirt)",
        labels=["vm"],
    )
    vm_cpu_time = GaugeMetricFamily(
        "huy_vm_cpu_time_seconds_total",
        "Total CPU time consumed by the domain (seconds)",
        labels=["vm"],
    )
    vm_block_read = GaugeMetricFamily(
        "huy_vm_block_read_bytes_total",
        "Cumulative block device read bytes",
        labels=["vm", "device"],
    )
    vm_block_write = GaugeMetricFamily(
        "huy_vm_block_write_bytes_total",
        "Cumulative block device write bytes",
        labels=["vm", "device"],
    )
    vm_status = GaugeMetricFamily(
        "huy_vm_agent_status",
        "Agent-reported VM status (1=matches label status)",
        labels=["vm", "status"],
    )

    state_counts: dict[str, int] = {}
    for name in state.libvirt.list_domains():
        try:
            _code, lv_state = state.libvirt.domain_state(name)
        except Exception:
            lv_state = "UNKNOWN"
        state_counts[lv_state] = state_counts.get(lv_state, 0) + 1

        st = state.monitor.get_status(name)
        for status in ("off", "on", "degraded"):
            vm_status.add_metric([name, status], 1.0 if st.get("status") == status else 0.0)

        if not state.libvirt.connected:
            continue
        try:
            dom = state.libvirt.lookup_domain(name)
            info = dom.info()
            # maxMem, memory KiB, vcpus, cpuTime ns
            max_mem_kib, mem_kib, vcpus, cpu_time_ns = info[1], info[2], info[3], info[4]
            vm_vcpu.add_metric([name], float(vcpus))
            vm_mem_max.add_metric([name], float(max_mem_kib) * 1024)
            vm_cpu_time.add_metric([name], float(cpu_time_ns) / 1e9)
            if dom.isActive():
                vm_mem_used.add_metric([name], float(mem_kib) * 1024)
                try:
                    stats = dom.memoryStats()
                    rss = stats.get("rss") or stats.get("actual")
                    if rss is not None:
                        vm_mem_used.add_metric([name], float(rss) * 1024)
                except Exception:
                    pass
                xml = dom.XMLDesc(0)
                for dev in _block_devices_from_xml(xml):
                    try:
                        rd_req, rd_bytes, wr_req, wr_bytes, _errs = dom.blockStats(dev)
                        vm_block_read.add_metric([name, dev], float(rd_bytes))
                        vm_block_write.add_metric([name, dev], float(wr_bytes))
                    except Exception:
                        continue
        except Exception as exc:
            logger.debug("vm_metrics_collect_failed", vm=name, error=str(exc))

    for lv_state, count in state_counts.items():
        vm_count.add_metric([lv_state], float(count))

    families.extend(
        [
            vm_count,
            vm_vcpu,
            vm_mem_max,
            vm_mem_used,
            vm_cpu_time,
            vm_block_read,
            vm_block_write,
            vm_status,
        ]
    )
    return families


def _block_devices_from_xml(xml: str) -> list[str]:
    import xml.etree.ElementTree as ET

    root = ET.fromstring(xml)
    devices: list[str] = []
    for disk in root.findall(".//devices/disk"):
        target = disk.find("target")
        if target is not None and target.get("dev"):
            devices.append(target.get("dev"))
    return devices or ["vda"]


class HuyMetricsCollector:
    """Dynamic Prometheus collector for hypervisor and VM metrics."""

    def __init__(self, state: AppState) -> None:
        self._state = state

    def collect(self):
        data_dir = str(self._state.settings.data_dir)
        yield from _collect_host(data_dir)
        yield from _collect_libvirt(self._state)

        agent = GaugeMetricFamily(
            "huy_agent_info",
            "Agent build and identity (value is always 1)",
            labels=["version", "hostname", "country", "city", "company"],
        )
        labels = self._state.settings.agent_labels
        from huy_libvirt_agent import __version__

        agent.add_metric(
            [
                __version__,
                self._state.hostname,
                labels["country"],
                labels["city"],
                labels["company"],
            ],
            1.0,
        )
        yield agent


def register_metrics_collector(state: AppState) -> None:
    global _COLLECTOR_REGISTERED
    if _COLLECTOR_REGISTERED:
        return
    REGISTRY.register(HuyMetricsCollector(state))
    _COLLECTOR_REGISTERED = True
