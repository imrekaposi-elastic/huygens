"""VM API schemas."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from huy_libvirt_agent.api.schemas.agent import AgentLabels


class CloudInitSpec(BaseModel):
    user_data: str = Field(..., description="#cloud-config YAML")
    meta_data: str = Field(default="instance-id: local\n")
    network_config: str | None = None


class VMCreateRequest(BaseModel):
    name: str = Field(..., pattern=r"^[a-zA-Z0-9._-]+$", examples=["web-01"])
    image: str = Field(..., description="HTTP(S) URL or local path to qcow2 image")
    vcpu: int = Field(default=2, ge=1, le=128)
    memory_mib: int = Field(default=2048, ge=256)
    network: str = Field(default="default", description="libvirt network name")
    cloud_init: CloudInitSpec
    ssh_keys: list[str] = Field(default_factory=list)
    guest_ip: str | None = None
    start: bool = True


class VMPatchRequest(BaseModel):
    vcpu: int | None = Field(default=None, ge=1, le=128)
    memory_mib: int | None = Field(default=None, ge=256)
    autostart: bool | None = None


VmStatus = Literal["off", "on", "degraded"]


class VMResponse(BaseModel):
    name: str
    labels: AgentLabels
    status: VmStatus
    libvirt_state: str
    guest_ip: str | None = None
    vcpu: int
    memory_mib: int
    network: str
    autostart: bool = False
    last_checked_at: str | None = None
