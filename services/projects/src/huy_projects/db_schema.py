"""Idempotent schema upgrades for existing PostgreSQL volumes (Phase 6+)."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Connection

from huy_projects.models import Base


def apply_schema_upgrades(connection: Connection) -> None:
    """Create missing tables and add columns introduced after first deploy."""
    Base.metadata.create_all(connection)

    if connection.dialect.name != "postgresql":
        return

    connection.execute(
        text(
            "ALTER TABLE ip_pools "
            "ADD COLUMN IF NOT EXISTS pool_kind VARCHAR(16) NOT NULL DEFAULT 'vnet'"
        )
    )
