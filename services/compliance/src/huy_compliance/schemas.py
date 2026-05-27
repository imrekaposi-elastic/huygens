"""API schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

MoscowKind = Literal["must", "should", "could", "wont"]
ResourceType = Literal["project", "vm", "network"]


class ComplianceItemCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    slug: str | None = Field(default=None, max_length=64)
    description: str | None = None
    reference_url: str | None = Field(default=None, max_length=2048)
    moscow: MoscowKind = "should"
    target_level: str | None = Field(default=None, max_length=64)


class ComplianceItemUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    reference_url: str | None = Field(default=None, max_length=2048)
    moscow: MoscowKind | None = None
    target_level: str | None = Field(default=None, max_length=64)


class ComplianceItemOut(BaseModel):
    id: str
    organization_id: str
    name: str
    slug: str
    description: str | None
    reference_url: str | None
    moscow: str
    target_level: str | None
    created_at: datetime
    updated_at: datetime


class InfrastructureProviderComplianceSet(BaseModel):
    compliance_item_ids: list[str] = Field(default_factory=list)
    is_compliant: bool | None = None

    @field_validator("compliance_item_ids")
    @classmethod
    def _unique_items(cls, v: list[str]) -> list[str]:
        return list(dict.fromkeys(v))


class InfrastructureProviderComplianceOut(BaseModel):
    organization_id: str
    infrastructure_provider_id: str
    is_compliant: bool
    compliance_items: list[ComplianceItemOut]
    updated_at: datetime | None = None


class RegionComplianceSet(BaseModel):
    compliance_item_ids: list[str] = Field(default_factory=list)

    @field_validator("compliance_item_ids")
    @classmethod
    def _unique_items(cls, v: list[str]) -> list[str]:
        return list(dict.fromkeys(v))


class RegionComplianceOut(BaseModel):
    organization_id: str
    region_id: str
    compliance_items: list[ComplianceItemOut]


class TraitCreate(BaseModel):
    trait_key: str = Field(..., min_length=1, max_length=64, pattern=r"^[a-z0-9._-]+$")
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    moscow: MoscowKind = "should"


class TraitOut(BaseModel):
    id: str
    organization_id: str
    trait_key: str
    title: str
    description: str | None
    moscow: str
    infrastructure_provider_id: str | None = None
    region_id: str | None = None
    created_at: datetime


class AssetCriticalitySet(BaseModel):
    compliance_item_ids: list[str] = Field(default_factory=list)
    placement_note: str | None = Field(default=None, max_length=4000)

    @field_validator("compliance_item_ids")
    @classmethod
    def _unique_items(cls, v: list[str]) -> list[str]:
        return list(dict.fromkeys(v))


class AssetCriticalityOut(BaseModel):
    organization_id: str
    resource_type: ResourceType
    project_id: str
    agent_id: str | None = None
    name: str | None = None
    compliance_items: list[ComplianceItemOut]
    inherited_compliance_items: list[ComplianceItemOut] = Field(default_factory=list)
    aggregate_compliance_items: list[ComplianceItemOut] = Field(
        default_factory=list,
        description="Project only: standards satisfied by every VM and network in the project",
    )
    placement_note: str | None
    updated_at: datetime | None = None


class ComplianceCheckCreate(BaseModel):
    compliance_item_id: str
    owner_user_id: str
    owner_display: str | None = None
    valid_until: datetime
    status: Literal["active", "expired", "waived"] = "active"


class ComplianceCheckUpdate(BaseModel):
    owner_user_id: str | None = None
    owner_display: str | None = None
    valid_until: datetime | None = None
    status: Literal["active", "expired", "waived"] | None = None
    last_reviewed_at: datetime | None = None


class ComplianceCheckOut(BaseModel):
    id: str
    organization_id: str
    compliance_item_id: str
    compliance_item_name: str | None = None
    owner_user_id: str
    owner_display: str | None
    valid_until: datetime
    status: str
    last_reviewed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    days_until_expiry: int | None = None


class TraitSummary(BaseModel):
    scope: Literal["provider", "region"]
    trait_key: str
    title: str
    description: str | None
    moscow: str
    infrastructure_provider_id: str | None = None
    infrastructure_provider_name: str | None = None
    region_id: str | None = None
    region_name: str | None = None


class PlacementRationaleOut(BaseModel):
    organization_id: str
    resource_type: ResourceType
    project_id: str
    agent_id: str | None = None
    name: str | None = None
    project_name: str | None = None
    agent_name: str | None = None
    region_id: str | None = None
    infrastructure_provider_id: str | None = None
    inherited_traits: list[TraitSummary]
    compliance_items: list[ComplianceItemOut]
    inherited_compliance_items: list[ComplianceItemOut] = Field(default_factory=list)
    placement_note: str | None
    related_checks: list[ComplianceCheckOut]
    config_drift: bool | None = None


class ComplianceDashboardOut(BaseModel):
    organization_id: str
    catalog_count: int
    checks_active: int
    checks_expiring_soon: int
    checks_expired: int
    assignments_count: int
    provider_traits_count: int
    region_traits_count: int


class ComplianceExplorerRow(BaseModel):
    resource_type: ResourceType
    project_id: str
    project_name: str | None = None
    agent_id: str | None = None
    agent_name: str | None = None
    name: str | None = None
    region_id: str | None = None
    region_name: str | None = None
    infrastructure_provider_id: str | None = None
    catalog_items: list[ComplianceItemOut]
    direct_catalog_items: list[ComplianceItemOut] = Field(default_factory=list)
    inherited_catalog_items: list[ComplianceItemOut] = Field(default_factory=list)
    aggregate_catalog_items: list[ComplianceItemOut] = Field(
        default_factory=list,
        description="Project only: standards every child VM/network satisfies",
    )
    inherited_traits: list[TraitSummary]
    placement_note: str | None = None


class ComplianceExplorerOut(BaseModel):
    organization_id: str
    filter_description: str
    total_matched: int
    offset: int = 0
    page_size: int = 25
    truncated: bool = False
    rows: list[ComplianceExplorerRow]


class ComplianceExplorerSuggestion(BaseModel):
    resource_key: str
    resource_type: ResourceType
    label: str
    project_id: str
    project_name: str | None = None
    agent_id: str | None = None
    name: str | None = None


class ComplianceExplorerSuggestOut(BaseModel):
    organization_id: str
    query: str
    suggestions: list[ComplianceExplorerSuggestion]


class ComplianceExplorerFacetsOut(BaseModel):
    organization_id: str
    catalog_items: list[ComplianceItemOut]
    trait_keys: list[str]
