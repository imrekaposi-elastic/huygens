"""libvirt connection wrapper with optional mock for dev."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

import structlog

from huy_libvirt_agent.services.libvirt_errors import (
    LibvirtError,  # re-exported for existing imports
    libvirt_wrapped,
    translate_libvirt_exception,
)
from huy_libvirt_agent.services.system_networks import network_access_flags

logger = structlog.get_logger(__name__)

try:
    import libvirt

    LIBVIRT_AVAILABLE = True
except ImportError:
    libvirt = None  # type: ignore
    LIBVIRT_AVAILABLE = False


class LibvirtClient:
    def __init__(self, uri: str = "qemu:///system") -> None:
        self.uri = uri
        self._conn: Any = None

    def connect(self) -> None:
        if not LIBVIRT_AVAILABLE:
            logger.warning("libvirt_python_not_installed", uri=self.uri)
            return
        try:
            self._conn = libvirt.open(self.uri)
        except Exception as exc:
            raise translate_libvirt_exception(exc) from exc
        if self._conn is None:
            raise LibvirtError(f"Failed to connect to {self.uri}", "CONNECTION_FAILED")

    @libvirt_wrapped
    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    @property
    def connected(self) -> bool:
        return self._conn is not None

    def _require(self) -> Any:
        if self._conn is None:
            raise LibvirtError("Not connected to libvirt", "NOT_CONNECTED")
        return self._conn

    @libvirt_wrapped
    def list_networks(self) -> list[dict]:
        if not self.connected:
            return []
        conn = self._require()
        result = []
        for net in conn.listAllNetworks():
            xml = net.XMLDesc(0)
            root = ET.fromstring(xml)
            bridge = root.find(".//bridge[@name]")
            net_name = net.name()
            readonly, deletable = network_access_flags(net_name, agent_managed=False)
            result.append(
                {
                    "name": net_name,
                    "uuid": net.UUIDString(),
                    "active": net.isActive(),
                    "bridge": bridge.get("name") if bridge is not None else None,
                    "xml": xml,
                    "readonly": readonly,
                    "deletable": deletable,
                }
            )
        return result

    @libvirt_wrapped
    def define_network_xml(self, xml: str) -> str:
        conn = self._require()
        net = conn.networkDefineXML(xml)
        return net.name()

    @libvirt_wrapped
    def network_lookup(self, name: str) -> Any:
        return self._require().networkLookupByName(name)

    @libvirt_wrapped
    def destroy_network(self, name: str) -> None:
        net = self.network_lookup(name)
        if net.isActive():
            net.destroy()
        net.undefine()

    @libvirt_wrapped
    def list_domains(self) -> list[str]:
        if not self.connected:
            return []
        return [d.name() for d in self._require().listAllDomains(0)]

    @libvirt_wrapped
    def define_domain_xml(self, xml: str) -> str:
        dom = self._require().defineXML(xml)
        if dom is None:
            raise LibvirtError("defineXML failed", "DEFINE_FAILED")
        return dom.name()

    @libvirt_wrapped
    def lookup_domain(self, name: str) -> Any:
        return self._require().lookupByName(name)

    @libvirt_wrapped
    def domain_state(self, name: str) -> tuple[int, str]:
        if not self.connected:
            return (5, "SHUTOFF")
        dom = self.lookup_domain(name)
        state, _ = dom.state()
        states = {
            0: "NOSTATE",
            1: "RUNNING",
            2: "BLOCKED",
            3: "PAUSED",
            4: "SHUTDOWN",
            5: "SHUTOFF",
            6: "CRASHED",
            7: "PMSUSPENDED",
        }
        return state, states.get(state, "UNKNOWN")

    @libvirt_wrapped
    def create_domain(self, name: str) -> None:
        dom = self.lookup_domain(name)
        if not dom.isActive():
            dom.create()

    @libvirt_wrapped
    def destroy_domain(self, name: str) -> None:
        dom = self.lookup_domain(name)
        if dom.isActive():
            dom.destroy()

    @libvirt_wrapped
    def undefine_domain(self, name: str) -> None:
        if not self.connected:
            return
        dom = self.lookup_domain(name)
        if dom.isActive():
            dom.destroy()
        flags = getattr(libvirt, "VIR_DOMAIN_UNDEFINE_NVRAM", 0) if LIBVIRT_AVAILABLE else 0
        dom.undefineFlags(flags)

    @libvirt_wrapped
    def domain_xml(self, name: str) -> str:
        return self.lookup_domain(name).XMLDesc(0)

    @libvirt_wrapped
    def set_domain_autostart(self, name: str, enabled: bool) -> None:
        dom = self.lookup_domain(name)
        if enabled:
            dom.setAutostart(1)
        else:
            dom.setAutostart(0)

    @libvirt_wrapped
    def domain_interface_addresses(self, name: str) -> list[str]:
        if not self.connected:
            return []
        dom = self.lookup_domain(name)
        if not dom.isActive():
            return []
        # Use DHCP lease only; guest-agent (qemu-ga) queries can block the libvirt worker for minutes.
        lease_src = getattr(libvirt, "VIR_DOMAIN_INTERFACE_ADDRESSES_SRC_LEASE", 2)
        try:
            ifaces = dom.interfaceAddresses(lease_src, 0)
        except Exception:
            return []
        ips = []
        for info in ifaces.values():
            for addr in info.get("addrs", []):
                if addr.get("type") == libvirt.VIR_IP_ADDR_TYPE_IPV4:
                    ips.append(addr["addr"])
        return ips

    @libvirt_wrapped
    def domain_runtime_metrics(self, name: str) -> dict | None:
        """Collect VM stats in one libvirt call chain (for metrics / read path)."""
        if not self.connected:
            return None
        dom = self.lookup_domain(name)
        info = dom.info()
        max_mem_kib, mem_kib, vcpus, cpu_time_ns = info[1], info[2], info[3], info[4]
        payload: dict = {
            "vcpus": float(vcpus),
            "memory_max_bytes": float(max_mem_kib) * 1024,
            "cpu_time_seconds": float(cpu_time_ns) / 1e9,
            "memory_used_bytes": None,
            "block_stats": [],
        }
        if dom.isActive():
            payload["memory_used_bytes"] = float(mem_kib) * 1024
            try:
                stats = dom.memoryStats()
                rss = stats.get("rss") or stats.get("actual")
                if rss is not None:
                    payload["memory_used_bytes"] = float(rss) * 1024
            except Exception:
                pass
            xml = dom.XMLDesc(0)
            for dev in _block_devices_from_xml(xml):
                try:
                    _rd_req, rd_bytes, _wr_req, wr_bytes, _errs = dom.blockStats(dev)
                    payload["block_stats"].append(
                        {"device": dev, "read_bytes": float(rd_bytes), "write_bytes": float(wr_bytes)}
                    )
                except Exception:
                    continue
        return payload


def _block_devices_from_xml(xml: str) -> list[str]:
    root = ET.fromstring(xml)
    devices: list[str] = []
    for disk in root.findall(".//devices/disk"):
        target = disk.find("target")
        if target is not None and target.get("dev"):
            devices.append(target.get("dev"))
    return devices or ["vda"]


@contextmanager
def libvirt_connection(uri: str) -> Generator[LibvirtClient, None, None]:
    client = LibvirtClient(uri)
    client.connect()
    try:
        yield client
    finally:
        client.close()
