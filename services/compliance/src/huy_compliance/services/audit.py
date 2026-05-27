"""Compliance change audit (PostgreSQL; export to ES in later phases)."""

from __future__ import annotations

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from huy_compliance.models import ComplianceAuditEvent

logger = structlog.get_logger(__name__)


async def record_audit(
    session: AsyncSession,
    *,
    organization_id: str,
    actor_user_id: str,
    action: str,
    entity_type: str,
    entity_id: str,
    detail: str | None = None,
) -> None:
    session.add(
        ComplianceAuditEvent(
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            detail=detail,
        )
    )
    logger.info(
        "compliance_audit",
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        detail=detail,
    )
