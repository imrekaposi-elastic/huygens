"""Registry ORM models."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _uuid() -> str:
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    pass


class Provider(Base):
    __tablename__ = "registry_providers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    regions: Mapped[list[Region]] = relationship(back_populates="provider")


class Region(Base):
    __tablename__ = "registry_regions"
    __table_args__ = (UniqueConstraint("provider_id", "slug", name="uq_region_provider_slug"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    provider_id: Mapped[str] = mapped_column(
        ForeignKey("registry_providers.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    provider: Mapped[Provider] = relationship(back_populates="regions")
    agents: Mapped[list[Agent]] = relationship(back_populates="region")


class Agent(Base):
    __tablename__ = "registry_agents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    base_url: Mapped[str] = mapped_column(String(512), nullable=False)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    provider_id: Mapped[str] = mapped_column(
        ForeignKey("registry_providers.id", ondelete="RESTRICT"), nullable=False
    )
    region_id: Mapped[str] = mapped_column(
        ForeignKey("registry_regions.id", ondelete="RESTRICT"), nullable=False
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

    provider: Mapped[Provider] = relationship()
    region: Mapped[Region] = relationship(back_populates="agents")
