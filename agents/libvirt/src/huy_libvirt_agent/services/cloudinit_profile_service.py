"""Reusable cloud-init profile registry (CRUD)."""

from __future__ import annotations

import shutil
from datetime import UTC, datetime
from pathlib import Path

from huy_libvirt_agent.api.schemas.agent import AgentLabels
from huy_libvirt_agent.api.schemas.image import (
    CloudInitProfileCreateRequest,
    CloudInitProfileResponse,
    CloudInitProfileUpdateRequest,
)
from huy_libvirt_agent.app_state import AppState
from huy_libvirt_agent.services.cloudinit import CloudInitBuilder
from huy_libvirt_agent.services.cloudinit_validator import CloudInitPayload, CloudInitValidator
from huy_libvirt_agent.services.libvirt_client import LibvirtError
from huy_libvirt_agent.services.metadata import read_metadata, write_metadata
from huy_libvirt_agent.services.path_safety import safe_child_dir


class CloudInitProfileService:
    def __init__(self, state: AppState) -> None:
        self._state = state
        self._profiles_dir = state.settings.data_dir / "cloud-init"
        self._profiles_dir.mkdir(parents=True, exist_ok=True)
        self._builder = CloudInitBuilder()
        self._validator = CloudInitValidator(state.settings.cloud_init_validation)

    def validate_payload(
        self,
        user_data: str,
        meta_data: str = "instance-id: local\n",
        network_config: str | None = None,
        ssh_keys: list[str] | None = None,
    ) -> None:
        self._validator.validate(
            CloudInitPayload(
                user_data=user_data,
                meta_data=meta_data,
                network_config=network_config,
                ssh_keys=ssh_keys or [],
            )
        )

    def _profile_dir(self, name: str) -> Path:
        return safe_child_dir(self._profiles_dir, name)

    def _meta_path(self, name: str) -> Path:
        return self._profile_dir(name) / "metadata.json"

    def list_profiles(self) -> list[CloudInitProfileResponse]:
        names = [p.name for p in self._profiles_dir.iterdir() if p.is_dir()]
        return [self.get_profile(n) for n in sorted(names)]

    def get_profile(self, name: str) -> CloudInitProfileResponse:
        meta = read_metadata(self._meta_path(name))
        if not meta:
            raise LibvirtError(f"Cloud-init profile {name} not found", "NOT_FOUND")
        return self._to_response(name, meta)

    def create_profile(
        self, body: CloudInitProfileCreateRequest, correlation_id: str | None = None
    ) -> CloudInitProfileResponse:
        if self._profile_dir(body.name).exists():
            raise LibvirtError(f"Cloud-init profile {body.name} already exists", "PROFILE_EXISTS")
        self.validate_payload(
            body.user_data,
            body.meta_data,
            body.network_config,
            body.ssh_keys,
        )
        now = datetime.now(UTC).isoformat()
        labels = self._state.settings.agent_labels
        meta = {
            "labels": labels,
            "user_data": body.user_data,
            "meta_data": body.meta_data,
            "network_config": body.network_config,
            "ssh_keys": body.ssh_keys,
            "created_at": now,
            "updated_at": now,
        }
        self._profile_dir(body.name).mkdir(parents=True)
        write_metadata(self._meta_path(body.name), meta)
        self._state.event_bus.publish(
            "huy.cloud_init.created",
            f"/hypervisors/{self._state.hostname}",
            {"name": body.name, "labels": labels},
            correlation_id=correlation_id,
        )
        return self._to_response(body.name, meta)

    def update_profile(
        self, name: str, body: CloudInitProfileUpdateRequest, correlation_id: str | None = None
    ) -> CloudInitProfileResponse:
        meta = read_metadata(self._meta_path(name))
        if not meta:
            raise LibvirtError(f"Cloud-init profile {name} not found", "NOT_FOUND")
        self.validate_payload(
            body.user_data if body.user_data is not None else meta["user_data"],
            body.meta_data if body.meta_data is not None else meta["meta_data"],
            body.network_config if body.network_config is not None else meta.get("network_config"),
            body.ssh_keys if body.ssh_keys is not None else meta.get("ssh_keys", []),
        )
        if body.user_data is not None:
            meta["user_data"] = body.user_data
        if body.meta_data is not None:
            meta["meta_data"] = body.meta_data
        if body.network_config is not None:
            meta["network_config"] = body.network_config
        if body.ssh_keys is not None:
            meta["ssh_keys"] = body.ssh_keys
        meta["updated_at"] = datetime.now(UTC).isoformat()
        write_metadata(self._meta_path(name), meta)
        self._state.event_bus.publish(
            "huy.cloud_init.updated",
            f"/hypervisors/{self._state.hostname}",
            {"name": name},
            correlation_id=correlation_id,
        )
        return self._to_response(name, meta)

    def delete_profile(self, name: str, correlation_id: str | None = None) -> None:
        pdir = self._profile_dir(name)
        if not pdir.exists():
            raise LibvirtError(f"Cloud-init profile {name} not found", "NOT_FOUND")
        shutil.rmtree(pdir)
        self._state.event_bus.publish(
            "huy.cloud_init.deleted",
            f"/hypervisors/{self._state.hostname}",
            {"name": name},
            correlation_id=correlation_id,
        )

    def build_iso(
        self,
        profile_name: str,
        output_iso: Path,
        *,
        instance_id: str | None = None,
        meta_data_override: str | None = None,
        extra_ssh_keys: list[str] | None = None,
    ) -> Path:
        meta = read_metadata(self._meta_path(profile_name))
        if not meta:
            raise LibvirtError(f"Cloud-init profile {profile_name} not found", "NOT_FOUND")
        meta_data = meta_data_override or meta["meta_data"]
        if instance_id and "instance-id:" not in meta_data:
            meta_data = f"instance-id: {instance_id}\nlocal-hostname: {instance_id}\n"
        ssh_keys = list(meta.get("ssh_keys", []))
        if extra_ssh_keys:
            ssh_keys.extend(extra_ssh_keys)
        return self._builder.build(
            output_iso,
            meta["user_data"],
            meta_data,
            meta.get("network_config"),
            ssh_keys,
        )

    def _to_response(self, name: str, meta: dict) -> CloudInitProfileResponse:
        labels = AgentLabels(**meta.get("labels", self._state.settings.agent_labels))
        return CloudInitProfileResponse(
            name=name,
            labels=labels,
            user_data=meta["user_data"],
            meta_data=meta["meta_data"],
            network_config=meta.get("network_config"),
            ssh_keys=meta.get("ssh_keys", []),
            created_at=meta["created_at"],
            updated_at=meta["updated_at"],
        )
