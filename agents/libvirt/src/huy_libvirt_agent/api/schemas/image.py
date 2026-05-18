"""Image and cloud-init profile API schemas."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

from huy_libvirt_agent.api.schemas.agent import AgentLabels

ImageStatus = Literal["pending", "ready", "error"]
ImageSourceType = Literal["url", "path"]


class ImageCreateRequest(BaseModel):
    name: str = Field(..., pattern=r"^[a-zA-Z0-9._-]+$", examples=["ubuntu-noble"])
    source: str = Field(..., description="HTTP(S) URL or absolute local path to qcow2/raw image")
    sha256: str | None = Field(default=None, description="Expected SHA-256 hex digest after download")
    fetch: bool = Field(default=True, description="Download or validate immediately")


class ImageUpdateRequest(BaseModel):
    source: str | None = None
    sha256: str | None = None
    refetch: bool = Field(default=False, description="Re-download or re-copy from source")


class ImageResponse(BaseModel):
    name: str
    labels: AgentLabels
    source: str
    source_type: ImageSourceType
    status: ImageStatus
    cached_path: str | None = None
    size_bytes: int | None = None
    sha256: str | None = None
    error: str | None = None
    created_at: str
    updated_at: str


class CloudInitProfileCreateRequest(BaseModel):
    name: str = Field(..., pattern=r"^[a-zA-Z0-9._-]+$", examples=["default-ssh"])
    user_data: str = Field(..., description="#cloud-config YAML")
    meta_data: str = Field(default="instance-id: local\n")
    network_config: str | None = None
    ssh_keys: list[str] = Field(default_factory=list)


class CloudInitProfileUpdateRequest(BaseModel):
    user_data: str | None = None
    meta_data: str | None = None
    network_config: str | None = None
    ssh_keys: list[str] | None = None


class CloudInitProfileResponse(BaseModel):
    name: str
    labels: AgentLabels
    user_data: str
    meta_data: str
    network_config: str | None = None
    ssh_keys: list[str] = Field(default_factory=list)
    created_at: str
    updated_at: str
