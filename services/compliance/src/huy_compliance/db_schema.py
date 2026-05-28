"""Schema initialization and idempotent upgrades for existing PostgreSQL volumes."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Connection

from huy_compliance.models import Base


def apply_schema_upgrades(connection: Connection) -> None:
    Base.metadata.create_all(connection)

    if connection.dialect.name != "postgresql":
        return

    connection.execute(
        text(
            "ALTER TABLE compliance_export_jobs "
            "ADD COLUMN IF NOT EXISTS generated_at TIMESTAMPTZ"
        )
    )
    connection.execute(
        text(
            "ALTER TABLE compliance_export_jobs "
            "ADD COLUMN IF NOT EXISTS requested_by_name VARCHAR(255)"
        )
    )
    connection.execute(
        text(
            "ALTER TABLE compliance_control_evidence "
            "ADD COLUMN IF NOT EXISTS supersedes_evidence_id VARCHAR(36)"
        )
    )
