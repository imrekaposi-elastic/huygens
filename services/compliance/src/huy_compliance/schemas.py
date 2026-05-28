"""API schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

MoscowKind = Literal["must", "should", "could", "wont"]
ResourceType = Literal["project", "vm", "network"]
EvidenceCategory = Literal["design", "implementation", "operating"]
CycleStatus = Literal["active", "planned", "closed"]
ExportJobStatus = Literal["queued", "running", "completed", "failed"]


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
    qualitative_characteristics: list[QualitativeCharacteristicOut] = Field(default_factory=list)


# ----------------------------
# Phase 7+ GRC schemas
# ----------------------------


class ComplianceStandardCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    slug: str | None = Field(default=None, max_length=64)
    description: str | None = None
    reference_url: str | None = Field(default=None, max_length=2048)
    moscow: MoscowKind = "should"
    target_level: str | None = Field(default=None, max_length=64)


class ComplianceStandardUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    reference_url: str | None = Field(default=None, max_length=2048)
    moscow: MoscowKind | None = None
    target_level: str | None = Field(default=None, max_length=64)


class ComplianceStandardOut(BaseModel):
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


class ComplianceControlCreate(BaseModel):
    control_code: str | None = Field(default=None, max_length=64)
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    rationale: str | None = None
    moscow: MoscowKind = "should"


class ComplianceControlUpdate(BaseModel):
    control_code: str | None = Field(default=None, max_length=64)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    rationale: str | None = None
    moscow: MoscowKind | None = None


class ComplianceControlOut(BaseModel):
    id: str
    organization_id: str
    standard_id: str
    control_code: str | None
    name: str
    description: str | None
    rationale: str | None
    moscow: str
    created_at: datetime
    updated_at: datetime


class ComplianceCycleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    status: CycleStatus = "active"
    starts_at: datetime | None = None
    ends_at: datetime | None = None


class ComplianceCycleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    status: CycleStatus | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None


class ComplianceCycleOut(BaseModel):
    id: str
    organization_id: str
    standard_id: str
    name: str
    status: str
    starts_at: datetime | None
    ends_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ComplianceCycleStatusOut(BaseModel):
    organization_id: str
    cycle_id: str
    standard_id: str
    cycle_name: str
    cycle_status: str

    controls_total: int
    controls_with_any_evidence: int

    evidence_by_category: dict[str, int] = Field(default_factory=dict)
    missing_evidence_controls_by_category: dict[str, int] = Field(default_factory=dict)

    checks_active: int
    checks_expiring_soon: int
    checks_expired: int


class ControlEvidenceOut(BaseModel):
    id: str
    organization_id: str
    control_id: str
    cycle_id: str | None
    category: str
    title: str
    summary: str | None
    file_name: str | None
    content_type: str | None
    size_bytes: int | None
    sha256: str | None
    tags: dict
    uploaded_by: str
    uploaded_at: datetime
    supersedes_evidence_id: str | None


class CompliancePackOut(BaseModel):
    id: str
    organization_id: str
    pack_key: str
    name: str
    vendor: str | None
    version: str | None
    imported_by: str
    imported_at: datetime


class CompliancePackImportIn(BaseModel):
    pack_key: str = Field(..., min_length=1, max_length=128)
    name: str = Field(..., min_length=1, max_length=255)
    vendor: str | None = Field(default=None, max_length=255)
    version: str | None = Field(default=None, max_length=64)
    payload: dict = Field(default_factory=dict, description="Raw pack JSON payload")


class CompliancePackValidateOut(BaseModel):
    pack_key: str
    name: str
    vendor: str | None = None
    version: str | None = None

    standards_to_create: int = 0
    controls_to_create: int = 0
    errors: list[str] = Field(default_factory=list)


class ComplianceExportRequest(BaseModel):
    export_type: Literal["pdf"] = "pdf"
    standard_id: str | None = None
    cycle_id: str | None = None


class ComplianceExportJobOut(BaseModel):
    id: str
    organization_id: str
    export_type: str
    status: str
    requested_by: str
    standard_id: str | None
    cycle_id: str | None
    error_message: str | None
    generated_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class QualitativeCharacteristicCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    slug: str | None = Field(default=None, max_length=64)
    description: str | None = None
    moscow: MoscowKind = "should"
    kind: str = Field(default="placement", max_length=32)


class QualitativeCharacteristicUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    moscow: MoscowKind | None = None
    kind: str | None = Field(default=None, max_length=32)


class QualitativeCharacteristicOut(BaseModel):
    id: str
    organization_id: str
    name: str
    slug: str
    description: str | None
    moscow: str
    kind: str
    created_at: datetime
    updated_at: datetime


class CharacteristicLinkSet(BaseModel):
    characteristic_ids: list[str] = Field(default_factory=list)

    @field_validator("characteristic_ids")
    @classmethod
    def _unique_characteristics(cls, v: list[str]) -> list[str]:
        return list(dict.fromkeys(v))


class LegacyTraitsMigrateOut(BaseModel):
    provider_traits_seen: int
    region_traits_seen: int
    characteristics_created: int
    provider_links_added: int
    region_links_added: int
