"""API request/response models."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ProjectCreate(BaseModel):
    organization_id: str = Field(min_length=1, max_length=36)
    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9][a-z0-9-]*$")
    description: str | None = None


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    name: str
    slug: str
    description: str | None
    created_at: datetime
    updated_at: datetime


class ProjectResourceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    agent_id: str
    resource_type: Literal["vm", "network", "cloud_init"]
    name: str
    desired_state: dict[str, Any] | None
    updated_at: datetime


class ResourceAssignmentOut(BaseModel):
    """Maps an agent VM/network/cloud-init name to a project (operator desired state)."""

    agent_id: str
    resource_type: Literal["vm", "network", "cloud_init"]
    name: str
    project_id: str
    project_name: str
    project_slug: str


class ResourceAssignRequest(BaseModel):
    resource_type: Literal["vm", "network", "cloud_init"]
    name: str = Field(min_length=1, max_length=255)


class AgentSummary(BaseModel):
    id: str
    name: str
    base_url: str
    organization_id: str
    agent_technology_id: str
    agent_technology_slug: str
    connection_status: str


class ProjectAgentTechnologyOut(BaseModel):
    agent_technology_id: str
    slug: str
    name: str
    description: str | None
    platform_enabled: bool
    enabled: bool


class ProjectAgentTechnologyItem(BaseModel):
    agent_technology_id: str
    enabled: bool


class ProjectAgentTechnologySet(BaseModel):
    technologies: list[ProjectAgentTechnologyItem]


class IpPoolCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    cidr: str = Field(examples=["10.100.0.0/16"])
    description: str | None = None
    exceptions: list[str] = Field(default_factory=list, description="Reserved CIDRs skipped by allocator")


class IpPoolOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    name: str
    cidr: str
    description: str | None
    exceptions: list[str]
    created_at: datetime


AllocationStatus = Literal["reserved", "allocated", "released"]


class IpAllocationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    pool_id: str
    project_id: str
    cidr: str
    network_name: str | None
    status: AllocationStatus
    created_at: datetime


class WizardPlanRequest(BaseModel):
    pool_id: str
    network_count: int = Field(ge=1, le=64)
    hosts_per_network: int = Field(ge=1, le=4096)
    exceptions: list[str] = Field(default_factory=list)


class WizardSubnetPlan(BaseModel):
    suggested_name: str
    cidr: str


class WizardPlanResponse(BaseModel):
    pool_id: str
    subnets: list[WizardSubnetPlan]


class WizardApplySubnet(BaseModel):
    cidr: str
    name: str | None = None


class WizardApplyRequest(BaseModel):
    pool_id: str
    subnets: list[WizardApplySubnet] = Field(min_length=1)
