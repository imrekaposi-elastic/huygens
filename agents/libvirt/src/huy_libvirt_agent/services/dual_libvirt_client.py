"""Libvirt client with separate write and read I/O paths (ADR 0006)."""

from __future__ import annotations

from typing import Any

from huy_libvirt_agent.services.libvirt_client import LibvirtClient
from huy_libvirt_agent.services.libvirt_queue import LibvirtQueue
from huy_libvirt_agent.services.system_networks import network_access_flags


class DualLibvirtClient:
    """
    Write path: serialized mutations on a dedicated connection + queue.
    Read path: list/state/metrics on a separate connection + queue (does not wait on writes).
    """

    def __init__(
        self,
        uri: str,
        write_queue: LibvirtQueue,
        read_queue: LibvirtQueue,
    ) -> None:
        self.uri = uri
        self._write = LibvirtClient(uri)
        self._read = LibvirtClient(uri)
        self._write_queue = write_queue
        self._read_queue = read_queue

    @property
    def queue(self) -> LibvirtQueue:
        """Write queue (backward compatible name)."""
        return self._write_queue

    @property
    def write_queue(self) -> LibvirtQueue:
        return self._write_queue

    @property
    def read_queue(self) -> LibvirtQueue:
        return self._read_queue

    @property
    def connected(self) -> bool:
        return self._write.connected and self._read.connected

    def connect(self) -> None:
        self._write_queue.run(self._write.connect)
        self._read_queue.run(self._read.connect)

    def close(self) -> None:
        if self._write.connected:
            self._write_queue.run(self._write.close)
        if self._read.connected:
            self._read_queue.run(self._read.close)

    # --- Read path ---

    def list_networks(self) -> list[dict]:
        return self._read_queue.run(self._read.list_networks)

    async def list_networks_async(self) -> list[dict]:
        return await self._read_queue.run_async(self._read.list_networks)

    def list_domains(self) -> list[str]:
        return self._read_queue.run(self._read.list_domains)

    async def list_domains_async(self) -> list[str]:
        return await self._read_queue.run_async(self._read.list_domains)

    def domain_state(self, name: str) -> tuple[int, str]:
        return self._read_queue.run(self._read.domain_state, name)

    async def domain_state_async(self, name: str) -> tuple[int, str]:
        return await self._read_queue.run_async(self._read.domain_state, name)

    def domain_interface_addresses(self, name: str) -> list[str]:
        return self._read_queue.run(self._read.domain_interface_addresses, name)

    async def domain_interface_addresses_async(self, name: str) -> list[str]:
        return await self._read_queue.run_async(self._read.domain_interface_addresses, name)

    def domain_xml(self, name: str) -> str:
        return self._read_queue.run(self._read.domain_xml, name)

    def domain_runtime_metrics(self, name: str) -> dict | None:
        return self._read_queue.run(self._read.domain_runtime_metrics, name)

    # --- Write path ---

    def define_network_xml(self, xml: str) -> str:
        return self._write_queue.run(self._write.define_network_xml, xml)

    def network_lookup(self, name: str) -> Any:
        return self._write_queue.run(self._write.network_lookup, name)

    def destroy_network(self, name: str) -> None:
        self._write_queue.run(self._write.destroy_network, name)

    def define_domain_xml(self, xml: str) -> str:
        return self._write_queue.run(self._write.define_domain_xml, xml)

    def lookup_domain(self, name: str) -> Any:
        """Prefer domain_runtime_metrics for read-side stats; mutations use write path."""
        return self._write_queue.run(self._write.lookup_domain, name)

    def create_domain(self, name: str) -> None:
        self._write_queue.run(self._write.create_domain, name)

    def destroy_domain(self, name: str) -> None:
        self._write_queue.run(self._write.destroy_domain, name)

    def undefine_domain(self, name: str) -> None:
        self._write_queue.run(self._write.undefine_domain, name)

    def set_domain_autostart(self, name: str, enabled: bool) -> None:
        self._write_queue.run(self._write.set_domain_autostart, name, enabled)


# Backward-compatible alias during Phase 1b transition.
QueuedLibvirtClient = DualLibvirtClient
