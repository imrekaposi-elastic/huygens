"""Cloud-init validation API schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class CloudInitValidateRequest(BaseModel):
    user_data: str = Field(..., description="#cloud-config YAML")
    meta_data: str = Field(default="instance-id: local\n")
    network_config: str | None = None
    ssh_keys: list[str] = Field(default_factory=list)


class ValidationIssueResponse(BaseModel):
    field: str
    path: str
    message: str
    line: int | None = None
    column: int | None = None


class CloudInitValidateResponse(BaseModel):
    valid: bool = True
    mode: str
    message: str = "Cloud-init configuration is valid"
