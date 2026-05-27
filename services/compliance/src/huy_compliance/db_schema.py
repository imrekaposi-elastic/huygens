"""Schema initialization."""

from __future__ import annotations

from sqlalchemy.engine import Connection

from huy_compliance.models import Base


def apply_schema_upgrades(connection: Connection) -> None:
    Base.metadata.create_all(connection)
