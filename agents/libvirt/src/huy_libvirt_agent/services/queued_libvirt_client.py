"""Libvirt client that routes all hypervisor calls through a work queue."""

from __future__ import annotations

from typing import Any

from huy_libvirt_agent.services.libvirt_client import LibvirtClient
from huy_libvirt_agent.services.libvirt_queue import LibvirtQueue


class QueuedLibvirtClient:
    """Thread-safe facade: one libvirt connection, serialized (by default) access."""

    def __init__(self, uri: str, queue: LibvirtQueue) -> None:
        self._inner = LibvirtClient(uri)
        self._queue = queue
        self.uri = uri

    @property
    def queue(self) -> LibvirtQueue:
        return self._queue

    @property
    def connected(self) -> bool:
        return self._inner.connected

    def connect(self) -> None:
        self._queue.run(self._inner.connect)

    def close(self) -> None:
        self._queue.run(self._inner.close)

    def list_networks(self) -> list[dict]:
        return self._queue.run(self._inner.list_networks)

    def define_network_xml(self, xml: str) -> str:
        return self._queue.run(self._inner.define_network_xml, xml)

    def network_lookup(self, name: str) -> Any:
        return self._queue.run(self._inner.network_lookup, name)

    def destroy_network(self, name: str) -> None:
        self._queue.run(self._inner.destroy_network, name)

    def list_domains(self) -> list[str]:
        return self._queue.run(self._inner.list_domains)

    def define_domain_xml(self, xml: str) -> str:
        return self._queue.run(self._inner.define_domain_xml, xml)

    def lookup_domain(self, name: str) -> Any:
        return self._queue.run(self._inner.lookup_domain, name)

    def domain_state(self, name: str) -> tuple[int, str]:
        return self._queue.run(self._inner.domain_state, name)

    def create_domain(self, name: str) -> None:
        self._queue.run(self._inner.create_domain, name)

    def destroy_domain(self, name: str) -> None:
        self._queue.run(self._inner.destroy_domain, name)

    def undefine_domain(self, name: str) -> None:
        self._queue.run(self._inner.undefine_domain, name)

    def domain_xml(self, name: str) -> str:
        return self._queue.run(self._inner.domain_xml, name)

    def set_domain_autostart(self, name: str, enabled: bool) -> None:
        self._queue.run(self._inner.set_domain_autostart, name, enabled)

    def domain_interface_addresses(self, name: str) -> list[str]:
        return self._queue.run(self._inner.domain_interface_addresses, name)
