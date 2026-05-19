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
            result.append(
                {
                    "name": net.name(),
                    "uuid": net.UUIDString(),
                    "active": net.isActive(),
                    "bridge": bridge.get("name") if bridge is not None else None,
                    "xml": xml,
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


@contextmanager
def libvirt_connection(uri: str) -> Generator[LibvirtClient, None, None]:
    client = LibvirtClient(uri)
    client.connect()
    try:
        yield client
    finally:
        client.close()
