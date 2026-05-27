"""Projects ORM models."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import JSON


def _uuid() -> str:
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    pass


class ProjectAgentTechnology(Base):
    """Which agent technologies (libvirt-agent, …) are enabled for a project."""

    __tablename__ = "project_agent_technologies"
    __table_args__ = (
        UniqueConstraint("project_id", "agent_technology_id", name="uq_project_agent_technology"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    agent_technology_id: Mapped[str] = mapped_column(String(36), nullable=False)
    agent_technology_slug: Mapped[str] = mapped_column(String(64), nullable=False)
    enabled: Mapped[bool] = mapped_column(default=False, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )


class Project(Base):
    __tablename__ = "projects"
    __table_args__ = (UniqueConstraint("organization_id", "slug", name="uq_project_org_slug"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )


class ProjectResource(Base):
    """Desired-state record for operator-managed resources (Phase 3)."""

    __tablename__ = "project_resources"
    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "agent_id",
            "resource_type",
            "name",
            name="uq_project_resource",
        ),
        UniqueConstraint(
            "agent_id",
            "resource_type",
            "name",
            name="uq_agent_resource_exclusive",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    agent_id: Mapped[str] = mapped_column(String(36), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    desired_state: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )


class IpPool(Base):
    """RFC1918 address pool per organization (Phase 4)."""

    __tablename__ = "ip_pools"
    __table_args__ = (UniqueConstraint("organization_id", "name", name="uq_ip_pool_org_name"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    cidr: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    exceptions: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    pool_kind: Mapped[str] = mapped_column(String(16), nullable=False, default="vnet")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class NetworkLink(Base):
    """WireGuard link between two project vnets on different agents (Phase 6)."""

    __tablename__ = "network_links"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    link_type: Mapped[str] = mapped_column(String(32), nullable=False, default="wireguard")
    left_agent_id: Mapped[str] = mapped_column(String(36), nullable=False)
    left_project_id: Mapped[str] = mapped_column(String(36), nullable=False)
    left_network_name: Mapped[str] = mapped_column(String(255), nullable=False)
    right_agent_id: Mapped[str] = mapped_column(String(36), nullable=False)
    right_project_id: Mapped[str] = mapped_column(String(36), nullable=False)
    right_network_name: Mapped[str] = mapped_column(String(255), nullable=False)
    overlay_pool_id: Mapped[str] = mapped_column(String(36), nullable=False)
    tunnel_cidr: Mapped[str] = mapped_column(String(64), nullable=False)
    left_tunnel_address: Mapped[str] = mapped_column(String(64), nullable=False)
    right_tunnel_address: Mapped[str] = mapped_column(String(64), nullable=False)
    left_public_key: Mapped[str] = mapped_column(String(128), nullable=False)
    right_public_key: Mapped[str] = mapped_column(String(128), nullable=False)
    left_private_key_enc: Mapped[str] = mapped_column(Text, nullable=False)
    right_private_key_enc: Mapped[str] = mapped_column(Text, nullable=False)
    left_vnet_cidr: Mapped[str | None] = mapped_column(String(64), nullable=True)
    right_vnet_cidr: Mapped[str | None] = mapped_column(String(64), nullable=True)
    config_drift: Mapped[bool] = mapped_column(default=False, nullable=False)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    desired_generation: Mapped[int] = mapped_column(default=1, nullable=False)
    applied_generation: Mapped[int] = mapped_column(default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )


class IpAllocation(Base):
    """Subnet carved from a pool for a project vnet."""

    __tablename__ = "ip_allocations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    pool_id: Mapped[str] = mapped_column(
        ForeignKey("ip_pools.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    cidr: Mapped[str] = mapped_column(String(64), nullable=False)
    network_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="reserved")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
