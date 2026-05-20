"""API request/response models."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


ConnectionStatus = Literal["pending", "connected", "error"]


class AgentTechnologyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    slug: str
    name: str
    description: str | None
    platform_enabled: bool
    created_at: datetime


class AgentTechnologyUpdate(BaseModel):
    platform_enabled: bool | None = None
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None


class InfrastructureProviderCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9][a-z0-9-]*$")


class InfrastructureProviderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    slug: str
    created_at: datetime
    operational: bool = False
    total_agents: int = 0


class RegionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9][a-z0-9-]*$")
    parent_region_id: str | None = Field(
        default=None,
        description="Parent region for sub-regions (datacenter → rack → …)",
    )


class RegionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    infrastructure_provider_id: str
    parent_region_id: str | None
    name: str
    slug: str
    created_at: datetime


class AgentOnRegionOut(BaseModel):
    id: str
    name: str
    base_url: str
    agent_technology_id: str
    agent_technology_slug: str
    connection_status: ConnectionStatus


class RegionTreeNode(BaseModel):
    id: str
    infrastructure_provider_id: str
    parent_region_id: str | None
    name: str
    slug: str
    has_direct_agent: bool
    operational: bool
    descendant_agent_count: int
    agents: list[AgentOnRegionOut]
    children: list[RegionTreeNode]


class InfrastructureProviderDetailOut(InfrastructureProviderOut):
    region_tree: list[RegionTreeNode]


class AgentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128, pattern=r"^[a-zA-Z0-9][a-zA-Z0-9_-]*$")
    base_url: HttpUrl
    organization_id: str = Field(min_length=1, max_length=36)
    infrastructure_provider_id: str
    region_id: str
    agent_technology_id: str
    refresh_seconds: int | None = Field(default=None, ge=10, le=3600)
    tls_verify: bool = True


class AgentUpdate(BaseModel):
    base_url: HttpUrl | None = None
    organization_id: str | None = None
    refresh_seconds: int | None = Field(default=None, ge=10, le=3600)
    tls_verify: bool | None = None
    connection_status: ConnectionStatus | None = None


class AgentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    base_url: str
    organization_id: str
    infrastructure_provider_id: str
    region_id: str
    agent_technology_id: str
    agent_technology_slug: str
    refresh_seconds: int
    tls_verify: bool
    connection_status: ConnectionStatus
    last_seen_at: datetime | None
    last_poll_error: str | None
    token_exported: bool
    created_at: datetime
    updated_at: datetime


class AgentCreated(AgentOut):
    agent_token: str


class AgentTokenExport(BaseModel):
    agent_token: str


class PollTargetOut(BaseModel):
    agent_id: str
    name: str
    organization_id: str
    region_id: str
    agent_technology_id: str
    base_url: str
    agent_token: str
    refresh_seconds: int
    tls_verify: bool
    connection_status: ConnectionStatus


class AgentConnectOut(BaseModel):
    agent_id: str
    organization_id: str
    base_url: str
    agent_token: str
    tls_verify: bool


class PollStatusUpdate(BaseModel):
    connection_status: ConnectionStatus
    last_seen_at: datetime | None = None
    last_poll_error: str | None = None


# Backward-compatible aliases (deprecated names)
ProviderCreate = InfrastructureProviderCreate
ProviderOut = InfrastructureProviderOut
