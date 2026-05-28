"""Compliance ORM models (PostgreSQL system of record)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    JSON,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _uuid() -> str:
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    pass


class OrgComplianceItem(Base):
    __tablename__ = "compliance_catalog_items"
    __table_args__ = (UniqueConstraint("organization_id", "slug", name="uq_compliance_item_slug"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    reference_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    moscow: Mapped[str] = mapped_column(String(16), nullable=False, default="should")
    target_level: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class InfrastructureProviderCompliance(Base):
    """Org-scoped compliance posture for an infrastructure provider."""

    __tablename__ = "compliance_infrastructure_providers"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "infrastructure_provider_id",
            name="uq_provider_compliance",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    infrastructure_provider_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    is_compliant: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    item_links: Mapped[list[InfrastructureProviderComplianceItemLink]] = relationship(
        back_populates="profile",
        cascade="all, delete-orphan",
    )


class InfrastructureProviderComplianceItemLink(Base):
    __tablename__ = "compliance_infrastructure_provider_items"
    __table_args__ = (
        UniqueConstraint("profile_id", "compliance_item_id", name="uq_provider_compliance_item"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    profile_id: Mapped[str] = mapped_column(
        ForeignKey("compliance_infrastructure_providers.id", ondelete="CASCADE"),
        nullable=False,
    )
    compliance_item_id: Mapped[str] = mapped_column(
        ForeignKey("compliance_catalog_items.id", ondelete="CASCADE"),
        nullable=False,
    )
    profile: Mapped[InfrastructureProviderCompliance] = relationship(back_populates="item_links")


class RegionComplianceItemLink(Base):
    """Catalog standards that apply to a region (inherited by agents in that region)."""

    __tablename__ = "compliance_region_items"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "region_id",
            "compliance_item_id",
            name="uq_region_compliance_item",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    region_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    compliance_item_id: Mapped[str] = mapped_column(
        ForeignKey("compliance_catalog_items.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ProviderTrait(Base):
    __tablename__ = "compliance_provider_traits"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "infrastructure_provider_id",
            "trait_key",
            name="uq_provider_trait_key",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    infrastructure_provider_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    trait_key: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    moscow: Mapped[str] = mapped_column(String(16), nullable=False, default="should")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class RegionTrait(Base):
    __tablename__ = "compliance_region_traits"
    __table_args__ = (
        UniqueConstraint("organization_id", "region_id", "trait_key", name="uq_region_trait_key"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    region_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    trait_key: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    moscow: Mapped[str] = mapped_column(String(16), nullable=False, default="should")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class AssetCriticalityAssignment(Base):
    __tablename__ = "compliance_asset_assignments"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "resource_type",
            "resource_key",
            name="uq_asset_assignment_resource",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(32), nullable=False)
    resource_key: Mapped[str] = mapped_column(String(512), nullable=False)
    placement_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    item_links: Mapped[list[AssetCriticalityItemLink]] = relationship(
        back_populates="assignment",
        cascade="all, delete-orphan",
    )


class AssetCriticalityItemLink(Base):
    __tablename__ = "compliance_asset_item_links"
    __table_args__ = (
        UniqueConstraint("assignment_id", "compliance_item_id", name="uq_assignment_item"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    assignment_id: Mapped[str] = mapped_column(
        ForeignKey("compliance_asset_assignments.id", ondelete="CASCADE"), nullable=False
    )
    compliance_item_id: Mapped[str] = mapped_column(
        ForeignKey("compliance_catalog_items.id", ondelete="CASCADE"), nullable=False
    )
    assignment: Mapped[AssetCriticalityAssignment] = relationship(back_populates="item_links")


class ComplianceCheck(Base):
    __tablename__ = "compliance_checks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    compliance_item_id: Mapped[str] = mapped_column(
        ForeignKey("compliance_catalog_items.id", ondelete="CASCADE"), nullable=False
    )
    owner_user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    owner_display: Mapped[str | None] = mapped_column(String(255), nullable=True)
    valid_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    last_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class ComplianceAuditEvent(Base):
    """Transactional audit row (search/export to ES in later phases)."""

    __tablename__ = "compliance_audit_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    actor_user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(36), nullable=False)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


# ----------------------------
# Phase 7+ GRC extensions (additive tables; no migrations yet)
# ----------------------------


class OrgComplianceStandard(Base):
    """Org-level compliance standard (e.g. ISO27001, BIO)."""

    __tablename__ = "compliance_standards"
    __table_args__ = (
        UniqueConstraint("organization_id", "slug", name="uq_compliance_standard_slug"),
        Index("ix_compliance_standards_org_updated", "organization_id", "updated_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    reference_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    moscow: Mapped[str] = mapped_column(String(16), nullable=False, default="should")
    target_level: Mapped[str | None] = mapped_column(String(64), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    controls: Mapped[list[OrgComplianceControl]] = relationship(
        back_populates="standard",
        cascade="all, delete-orphan",
    )
    cycles: Mapped[list[OrgComplianceCycle]] = relationship(
        back_populates="standard",
        cascade="all, delete-orphan",
    )


class OrgComplianceControl(Base):
    """A control under a standard (e.g. ISO27001 A.8.1)."""

    __tablename__ = "compliance_controls"
    __table_args__ = (
        UniqueConstraint("standard_id", "control_code", name="uq_control_code_per_standard"),
        Index("ix_compliance_controls_org_standard", "organization_id", "standard_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    standard_id: Mapped[str] = mapped_column(
        ForeignKey("compliance_standards.id", ondelete="CASCADE"), nullable=False, index=True
    )

    control_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    moscow: Mapped[str] = mapped_column(String(16), nullable=False, default="should")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    standard: Mapped[OrgComplianceStandard] = relationship(back_populates="controls")
    evidence: Mapped[list[OrgControlEvidence]] = relationship(
        back_populates="control",
        cascade="all, delete-orphan",
    )


class OrgComplianceCycle(Base):
    """A repeated assessment cycle for a given standard (e.g. 2026 audit cycle)."""

    __tablename__ = "compliance_cycles"
    __table_args__ = (
        UniqueConstraint("standard_id", "name", name="uq_cycle_name_per_standard"),
        Index("ix_compliance_cycles_org_standard", "organization_id", "standard_id"),
        Index("ix_compliance_cycles_org_status", "organization_id", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    standard_id: Mapped[str] = mapped_column(
        ForeignKey("compliance_standards.id", ondelete="CASCADE"), nullable=False, index=True
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    standard: Mapped[OrgComplianceStandard] = relationship(back_populates="cycles")


class OrgControlEvidence(Base):
    """Evidence for a control in a cycle (bytes stored in object store; DB holds references)."""

    __tablename__ = "compliance_control_evidence"
    __table_args__ = (
        Index("ix_evidence_org_control_cycle", "organization_id", "control_id", "cycle_id"),
        Index("ix_evidence_org_cycle_category", "organization_id", "cycle_id", "category"),
        Index("ix_evidence_org_uploaded_at", "organization_id", "uploaded_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    control_id: Mapped[str] = mapped_column(
        ForeignKey("compliance_controls.id", ondelete="CASCADE"), nullable=False, index=True
    )
    cycle_id: Mapped[str | None] = mapped_column(
        ForeignKey("compliance_cycles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    category: Mapped[str] = mapped_column(String(32), nullable=False)  # design|implementation|operating
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    object_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_name: Mapped[str | None] = mapped_column(String(512), nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sha256: Mapped[str | None] = mapped_column(String(128), nullable=True)

    uploaded_by: Mapped[str] = mapped_column(String(36), nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    supersedes_evidence_id: Mapped[str | None] = mapped_column(
        ForeignKey("compliance_control_evidence.id", ondelete="SET NULL"),
        nullable=True,
    )

    tags: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    control: Mapped[OrgComplianceControl] = relationship(back_populates="evidence")


class OrgCompliancePack(Base):
    """Imported JSON pack that can seed standards/controls (keeps provenance)."""

    __tablename__ = "compliance_packs"
    __table_args__ = (
        UniqueConstraint("organization_id", "pack_key", name="uq_pack_key_per_org"),
        Index("ix_compliance_packs_org_imported", "organization_id", "imported_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)

    pack_key: Mapped[str] = mapped_column(String(128), nullable=False)  # e.g. iso27001:2022
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    vendor: Mapped[str | None] = mapped_column(String(255), nullable=True)
    version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    raw_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    imported_by: Mapped[str] = mapped_column(String(36), nullable=False)
    imported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ComplianceExportJob(Base):
    """Async export job (PDF first). Artifact stored in object store similarly to evidence."""

    __tablename__ = "compliance_export_jobs"
    __table_args__ = (
        Index("ix_export_jobs_org_created", "organization_id", "created_at"),
        Index("ix_export_jobs_org_status", "organization_id", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)

    export_type: Mapped[str] = mapped_column(String(32), nullable=False, default="pdf")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued")
    requested_by: Mapped[str] = mapped_column(String(36), nullable=False)
    requested_by_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    standard_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    cycle_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    artifact_object_key: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    artifact_content_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    artifact_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    artifact_sha256: Mapped[str | None] = mapped_column(String(128), nullable=True)

    generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class OrgQualitativeCharacteristic(Base):
    """Org-configurable qualitative characteristic (successor to free-form traits for UI/inheritance)."""

    __tablename__ = "compliance_qualitative_characteristics"
    __table_args__ = (
        UniqueConstraint("organization_id", "slug", name="uq_characteristic_slug"),
        Index("ix_characteristics_org_updated", "organization_id", "updated_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    moscow: Mapped[str] = mapped_column(String(16), nullable=False, default="should")
    kind: Mapped[str] = mapped_column(String(32), nullable=False, default="placement")  # placement|policy|other

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class InfrastructureProviderCharacteristicLink(Base):
    __tablename__ = "compliance_provider_characteristics"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "infrastructure_provider_id",
            "characteristic_id",
            name="uq_provider_characteristic",
        ),
        Index("ix_provider_characteristics_org_provider", "organization_id", "infrastructure_provider_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    infrastructure_provider_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    characteristic_id: Mapped[str] = mapped_column(
        ForeignKey("compliance_qualitative_characteristics.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class RegionCharacteristicLink(Base):
    __tablename__ = "compliance_region_characteristics"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "region_id",
            "characteristic_id",
            name="uq_region_characteristic",
        ),
        Index("ix_region_characteristics_org_region", "organization_id", "region_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    region_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    characteristic_id: Mapped[str] = mapped_column(
        ForeignKey("compliance_qualitative_characteristics.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ComplianceAuditLog(Base):
    """Append-only audit log with before/after snapshots (separate from legacy ComplianceAuditEvent)."""

    __tablename__ = "compliance_audit_log"
    __table_args__ = (
        Index("ix_audit_log_org_occurred", "organization_id", "occurred_at"),
        Index("ix_audit_log_org_entity", "organization_id", "entity_type", "entity_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)

    actor_user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    actor_roles: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(36), nullable=False)

    before_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    after_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(128), nullable=True)

    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


def utc_now() -> datetime:
    return datetime.now(UTC)


def ensure_utc(dt: datetime) -> datetime:
    """Normalize datetimes for DB columns and comparisons (naive → UTC)."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)
