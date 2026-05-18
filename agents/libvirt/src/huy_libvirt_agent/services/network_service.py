"""Virtual network lifecycle."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from huy_libvirt_agent.api.schemas.agent import AgentLabels
from huy_libvirt_agent.api.schemas.network import (
    NetworkCreateRequest,
    NetworkPatchRequest,
    NetworkResponse,
)
from huy_libvirt_agent.app_state import AppState
from huy_libvirt_agent.services.libvirt_client import LibvirtError
from huy_libvirt_agent.services.metadata import read_metadata, write_metadata
from huy_libvirt_agent.services.network_xml import render_network_xml


class NetworkService:
    def __init__(self, state: AppState) -> None:
        self._state = state

    def _vnet_dir(self, name: str) -> Path:
        return self._state.settings.data_dir / "vnets" / name

    def list_networks(self) -> list[NetworkResponse]:
        managed = {
            p.name
            for p in (self._state.settings.data_dir / "vnets").glob("*")
            if p.is_dir()
        }
        libvirt_nets = {n["name"]: n for n in self._state.libvirt.list_networks()}
        all_names = sorted(managed | set(libvirt_nets.keys()))
        return [self.get_network(n, libvirt_nets.get(n)) for n in all_names]

    def get_network(self, name: str, lv_info: dict | None = None) -> NetworkResponse:
        meta_path = self._vnet_dir(name) / "metadata.json"
        meta = read_metadata(meta_path)
        labels = AgentLabels(**meta.get("labels", self._state.settings.agent_labels))
        if lv_info is None:
            for n in self._state.libvirt.list_networks():
                if n["name"] == name:
                    lv_info = n
                    break
        dnat_path = self._vnet_dir(name) / "dnat.json"
        dnat_count = 0
        if dnat_path.exists():
            dnat_count = len(json.loads(dnat_path.read_text()))
        stored = self._state.iptables.checksum_for_vnet(name)
        in_sync = stored is not None
        return NetworkResponse(
            name=name,
            labels=labels,
            uuid=lv_info.get("uuid") if lv_info else None,
            active=lv_info.get("active", False) if lv_info else False,
            bridge=lv_info.get("bridge") if lv_info else meta.get("bridge"),
            ipv4_cidr=meta.get("ipv4_cidr"),
            dnat_rule_count=dnat_count,
            iptables_in_sync=in_sync,
        )

    def create_network(
        self, body: NetworkCreateRequest, correlation_id: str | None = None
    ) -> NetworkResponse:
        if self._vnet_dir(body.name).exists():
            raise LibvirtError(f"Network {body.name} exists", "NETWORK_EXISTS")
        bridge = body.bridge or f"br-{body.name}"
        xml = render_network_xml(body.name, bridge, body.ipv4_cidr, body.dhcp)
        labels = self._state.settings.agent_labels
        try:
            self._state.libvirt.define_network_xml(xml)
            net = self._state.libvirt.network_lookup(body.name)
            if not net.isActive():
                net.create()
            net.setAutostart(1)
        except LibvirtError:
            pass
        write_metadata(
            self._vnet_dir(body.name) / "metadata.json",
            {
                "labels": labels,
                "bridge": bridge,
                "ipv4_cidr": body.ipv4_cidr,
                "created_at": datetime.now(UTC).isoformat(),
            },
        )
        self._state.event_bus.publish(
            "huy.vnet.created",
            f"/hypervisors/{self._state.hostname}",
            {"name": body.name, "labels": labels},
            correlation_id=correlation_id,
        )
        return self.get_network(body.name)

    def patch_network(self, name: str, body: NetworkPatchRequest) -> NetworkResponse:
        meta_path = self._vnet_dir(name) / "metadata.json"
        meta = read_metadata(meta_path)
        if body.ipv4_cidr:
            meta["ipv4_cidr"] = body.ipv4_cidr
        write_metadata(meta_path, meta)
        return self.get_network(name)

    def delete_network(self, name: str, purge: bool = False, correlation_id: str | None = None) -> None:
        try:
            self._state.libvirt.destroy_network(name)
        except LibvirtError:
            pass
        vdir = self._vnet_dir(name)
        if purge and vdir.exists():
            import shutil

            shutil.rmtree(vdir)
        self._state.event_bus.publish(
            "huy.vnet.deleted",
            f"/hypervisors/{self._state.hostname}",
            {"name": name},
            correlation_id=correlation_id,
        )
