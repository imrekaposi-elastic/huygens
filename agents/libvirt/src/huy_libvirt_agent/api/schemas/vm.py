"""VM API schemas."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

from huy_libvirt_agent.api.schemas.agent import AgentLabels


class SshTrustInject(BaseModel):
    ca_public_key_openssh: str = Field(min_length=20)
    linux_username: str = Field(min_length=1, max_length=64)
    sudoers_lines: list[str] = Field(default_factory=list)
    default_shell: str = "/bin/bash"


class CloudInitSpec(BaseModel):
    user_data: str = Field(..., description="#cloud-config YAML")
    meta_data: str = Field(default="instance-id: local\n")
    network_config: str | None = None


class VMCreateRequest(BaseModel):
    name: str = Field(..., pattern=r"^[a-zA-Z0-9._-]+$", examples=["web-01"])
    image: str | None = Field(
        default=None,
        description="HTTP(S) URL or local path (omit if image_name is set)",
    )
    image_name: str | None = Field(
        default=None,
        description="Registered managed image name from GET /api/v1/images",
    )
    vcpu: int = Field(default=2, ge=1, le=128)
    memory_mib: int = Field(default=2048, ge=256)
    network: str = Field(default="default", description="libvirt network name")
    cloud_init: CloudInitSpec | None = None
    cloud_init_profile: str | None = Field(
        default=None,
        description="Registered cloud-init profile from GET /api/v1/cloud-init",
    )
    ssh_keys: list[str] = Field(
        default_factory=list,
        description="Extra SSH keys when using cloud_init_profile",
    )
    guest_ip: str | None = None
    start: bool = True
    ssh_trust: SshTrustInject | None = Field(
        default=None,
        description="Merge org SSH CA + linux user into cloud-init (set by projects on create)",
    )
    skip_ssh_trust: bool = Field(
        default=False,
        description="When true, do not merge ssh_trust even if present",
    )

    @model_validator(mode="after")
    def require_image_and_cloud_init(self) -> VMCreateRequest:
        if not self.image and not self.image_name:
            raise ValueError("Either image or image_name is required")
        if self.image and self.image_name:
            raise ValueError("Specify only one of image or image_name")
        if not self.cloud_init and not self.cloud_init_profile:
            raise ValueError("Either cloud_init or cloud_init_profile is required")
        if self.cloud_init and self.cloud_init_profile:
            raise ValueError("Specify only one of cloud_init or cloud_init_profile")
        return self


class VMPatchRequest(BaseModel):
    vcpu: int | None = Field(default=None, ge=1, le=128)
    memory_mib: int | None = Field(default=None, ge=256)
    autostart: bool | None = None
    confirm_reboot: bool = Field(
        default=False,
        description="Required when changing vCPU/memory on a running VM (stop → resize → start).",
    )


class VMDiskInfo(BaseModel):
    device: str
    path: str | None = None
    size_bytes: int | None = None


VmStatus = Literal["off", "on", "degraded"]


class VMResponse(BaseModel):
    name: str
    server_name: str = Field(description="Guest/server hostname (defaults to VM name)")
    labels: AgentLabels
    status: VmStatus
    libvirt_state: str
    guest_ip: str | None = None
    vcpu: int
    memory_mib: int
    disks: list[VMDiskInfo] = Field(default_factory=list)
    network: str
    autostart: bool = False
    last_checked_at: str | None = None
