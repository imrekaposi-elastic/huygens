"""VM lifecycle orchestration."""

from __future__ import annotations

import shutil
from datetime import UTC, datetime
from pathlib import Path

from huy_libvirt_agent.api.schemas.agent import AgentLabels
from huy_libvirt_agent.api.schemas.vm import VMDiskInfo, VMCreateRequest, VMPatchRequest, VMResponse
from huy_libvirt_agent.app_state import AppState
from huy_libvirt_agent.services.cloudinit import CloudInitBuilder
from huy_libvirt_agent.services.cloudinit_profile_service import CloudInitProfileService
from huy_libvirt_agent.services.domain_xml import (
    parse_domain_disks,
    parse_domain_resources,
    render_domain_xml,
    update_domain_xml_resources,
)
from huy_libvirt_agent.services.image_service import ImageService
from huy_libvirt_agent.services.image_store import ImageStore
from huy_libvirt_agent.services.libvirt_client import LibvirtError
from huy_libvirt_agent.services.metadata import read_metadata, write_metadata
from huy_libvirt_agent.services.path_safety import safe_child_dir


class VMService:
    def __init__(self, state: AppState) -> None:
        self._state = state
        self._image_registry = ImageService(state)
        self._images = ImageStore(
            state.settings.data_dir / "images" / "cache",
            state.settings.image_download_timeout_seconds,
        )
        self._cloudinit_profiles = CloudInitProfileService(state)

    def _instance_dir(self, name: str) -> Path:
        return safe_child_dir(self._state.settings.data_dir / "instances", name)

    def list_vms(self) -> list[VMResponse]:
        names = set(self._state.libvirt.list_domains())
        for p in (self._state.settings.data_dir / "instances").glob("*"):
            if p.is_dir():
                names.add(p.name)
        return [self.get_vm(n) for n in sorted(names)]

    def get_vm(self, name: str) -> VMResponse:
        meta_path = self._instance_dir(name) / "metadata.json"
        meta = read_metadata(meta_path)
        labels = AgentLabels(**meta.get("labels", self._state.settings.agent_labels))
        st = self._state.monitor.get_status(name)
        libvirt_state = st.get("libvirt_state", "SHUTOFF")
        vcpu = meta.get("vcpu", 1)
        memory_mib = meta.get("memory_mib", 1024)
        disks: list[VMDiskInfo] = []
        try:
            _, libvirt_state = self._state.libvirt.domain_state(name)
            xml = self._state.libvirt.domain_xml(name)
            resources = parse_domain_resources(xml)
            if resources.get("vcpu") is not None:
                vcpu = resources["vcpu"]  # type: ignore[assignment]
            if resources.get("memory_mib") is not None:
                memory_mib = resources["memory_mib"]  # type: ignore[assignment]
            disks = [VMDiskInfo(**d) for d in parse_domain_disks(xml)]
        except LibvirtError:
            disk_path = self._instance_dir(name) / "disk.qcow2"
            if disk_path.exists():
                disks = [
                    VMDiskInfo(
                        device="vda",
                        path=str(disk_path),
                        size_bytes=disk_path.stat().st_size,
                    )
                ]
        return VMResponse(
            name=name,
            server_name=str(meta.get("server_name") or name),
            labels=labels,
            status=st.get("status", "off"),
            libvirt_state=libvirt_state,
            guest_ip=st.get("guest_ip"),
            vcpu=vcpu,
            memory_mib=memory_mib,
            disks=disks,
            network=meta.get("network", "default"),
            autostart=meta.get("autostart", False),
            last_checked_at=st.get("last_checked_at"),
        )

    def create_vm(self, body: VMCreateRequest, correlation_id: str | None = None) -> VMResponse:
        inst = self._instance_dir(body.name)
        if inst.exists():
            raise LibvirtError(f"VM {body.name} already exists", "DOMAIN_EXISTS")
        labels = self._state.settings.agent_labels
        if body.image_name:
            base = self._image_registry.resolve_disk_path(body.image_name)
        else:
            base = self._images.resolve_base_image(body.image)  # type: ignore[arg-type]
        disk = self._images.create_overlay(base, inst / "disk.qcow2")
        iso_path = inst / "cidata.iso"
        if body.cloud_init_profile:
            profile = self._cloudinit_profiles.get_profile(body.cloud_init_profile)
            merged_keys = list(profile.ssh_keys) + list(body.ssh_keys)
            self._cloudinit_profiles.validate_payload(
                profile.user_data,
                profile.meta_data,
                profile.network_config,
                merged_keys,
            )
        elif body.cloud_init:
            ci = body.cloud_init
            self._cloudinit_profiles.validate_payload(
                ci.user_data,
                ci.meta_data,
                ci.network_config,
                body.ssh_keys,
            )
        if body.cloud_init_profile:
            iso = self._cloudinit_profiles.build_iso(
                body.cloud_init_profile,
                iso_path,
                instance_id=body.name,
                extra_ssh_keys=body.ssh_keys or None,
            )
        else:
            ci = body.cloud_init
            iso = CloudInitBuilder().build(
                iso_path,
                ci.user_data,  # type: ignore[union-attr]
                ci.meta_data,  # type: ignore[union-attr]
                ci.network_config,  # type: ignore[union-attr]
                body.ssh_keys,
            )
        xml = render_domain_xml(
            body.name,
            labels,
            disk,
            iso,
            body.network,
            body.vcpu,
            body.memory_mib,
        )
        self._state.libvirt.define_domain_xml(xml)
        write_metadata(
            inst / "metadata.json",
            {
                "labels": labels,
                "server_name": body.name,
                "vcpu": body.vcpu,
                "memory_mib": body.memory_mib,
                "network": body.network,
                "guest_ip": body.guest_ip,
                "image_name": body.image_name,
                "cloud_init_profile": body.cloud_init_profile,
                "created_at": datetime.now(UTC).isoformat(),
            },
        )
        self._state.monitor.register_vm(body.name, body.guest_ip)
        if body.start:
            self._state.libvirt.create_domain(body.name)
        self._state.event_bus.publish(
            "huy.vm.created",
            f"/hypervisors/{self._state.hostname}",
            {"name": body.name, "labels": labels},
            correlation_id=correlation_id,
        )
        return self.get_vm(body.name)

    def patch_vm(self, name: str, body: VMPatchRequest) -> VMResponse:
        meta_path = self._instance_dir(name) / "metadata.json"
        meta = read_metadata(meta_path)
        resize = body.vcpu is not None or body.memory_mib is not None
        was_running = False
        if resize and self._state.libvirt.connected:
            try:
                _, state_name = self._state.libvirt.domain_state(name)
                was_running = state_name == "RUNNING"
            except LibvirtError:
                was_running = False
            if was_running and not body.confirm_reboot:
                raise LibvirtError(
                    "VM is running. Set confirm_reboot=true after operator approval to apply "
                    "memory/vCPU changes (the VM will be stopped and started again).",
                    "OPERATION_INVALID",
                )
            if was_running:
                self._state.libvirt.destroy_domain(name)
            xml = self._state.libvirt.domain_xml(name)
            xml = update_domain_xml_resources(
                xml,
                vcpu=body.vcpu if body.vcpu is not None else meta.get("vcpu"),
                memory_mib=body.memory_mib if body.memory_mib is not None else meta.get("memory_mib"),
            )
            self._state.libvirt.define_domain_xml(xml)
            if was_running:
                self._state.libvirt.create_domain(name)
        if body.autostart is not None:
            self._state.libvirt.set_domain_autostart(name, body.autostart)
            meta["autostart"] = body.autostart
        if body.vcpu is not None:
            meta["vcpu"] = body.vcpu
        if body.memory_mib is not None:
            meta["memory_mib"] = body.memory_mib
        write_metadata(meta_path, meta)
        return self.get_vm(name)

    def delete_vm(self, name: str, correlation_id: str | None = None) -> None:
        try:
            self._state.libvirt.undefine_domain(name)
        except LibvirtError:
            pass
        self._state.monitor.unregister_vm(name)
        inst = self._instance_dir(name)
        if inst.exists():
            shutil.rmtree(inst)
        self._state.event_bus.publish(
            "huy.vm.deleted",
            f"/hypervisors/{self._state.hostname}",
            {"name": name, "labels": self._state.settings.agent_labels},
            correlation_id=correlation_id,
        )
