"""Registry ORM models."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _uuid() -> str:
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    pass


class AgentTechnology(Base):
    """Technical agent implementation (e.g. libvirt-agent) — how inventory is collected."""

    __tablename__ = "agent_technologies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    platform_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class InfrastructureProvider(Base):
    """Functional cloud / vendor (Hetzner, Azure, on-prem rack estate, …)."""

    __tablename__ = "infrastructure_providers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    regions: Mapped[list[Region]] = relationship(
        back_populates="infrastructure_provider",
        foreign_keys="Region.infrastructure_provider_id",
    )


class Region(Base):
    """Location in an estate: datacenter, rack, city — may nest as sub-regions."""

    __tablename__ = "infrastructure_regions"
    __table_args__ = (
        UniqueConstraint(
            "infrastructure_provider_id",
            "parent_region_id",
            "slug",
            name="uq_region_parent_slug",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    infrastructure_provider_id: Mapped[str] = mapped_column(
        ForeignKey("infrastructure_providers.id", ondelete="CASCADE"), nullable=False
    )
    parent_region_id: Mapped[str | None] = mapped_column(
        ForeignKey("infrastructure_regions.id", ondelete="CASCADE"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    infrastructure_provider: Mapped[InfrastructureProvider] = relationship(
        back_populates="regions",
        foreign_keys=[infrastructure_provider_id],
    )
    parent: Mapped[Region | None] = relationship(
        remote_side="Region.id",
        foreign_keys=[parent_region_id],
    )
    agents: Mapped[list[Agent]] = relationship(back_populates="region")
    children: Mapped[list[Region]] = relationship(
        back_populates="parent",
        foreign_keys=[parent_region_id],
    )


class Agent(Base):
    """Enrolled hypervisor endpoint in a region, using one agent technology."""

    __tablename__ = "registry_agents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    base_url: Mapped[str] = mapped_column(String(512), nullable=False)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    infrastructure_provider_id: Mapped[str] = mapped_column(
        ForeignKey("infrastructure_providers.id", ondelete="RESTRICT"), nullable=False
    )
    region_id: Mapped[str] = mapped_column(
        ForeignKey("infrastructure_regions.id", ondelete="RESTRICT"), nullable=False
    )
    agent_technology_id: Mapped[str] = mapped_column(
        ForeignKey("agent_technologies.id", ondelete="RESTRICT"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    token_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    token_exported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    refresh_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    tls_verify: Mapped[bool] = mapped_column(default=True, nullable=False)
    connection_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_poll_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    infrastructure_provider: Mapped[InfrastructureProvider] = relationship()
    region: Mapped[Region] = relationship(back_populates="agents")
    agent_technology: Mapped[AgentTechnology] = relationship()
