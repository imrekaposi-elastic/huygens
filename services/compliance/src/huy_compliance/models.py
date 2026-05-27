"""Compliance ORM models (PostgreSQL system of record)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
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


def utc_now() -> datetime:
    return datetime.now(UTC)


def ensure_utc(dt: datetime) -> datetime:
    """Normalize datetimes for DB columns and comparisons (naive → UTC)."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)
