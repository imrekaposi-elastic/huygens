"""Compliance change audit (PostgreSQL; export to ES in later phases)."""

from __future__ import annotations

import structlog
from huy_events import try_publish_audit_event
from huy_telemetry.context import audit_log_fields, current_trace_ids
from sqlalchemy.ext.asyncio import AsyncSession

from huy_compliance.models import ComplianceAuditEvent

logger = structlog.get_logger(__name__)
COMPLIANCE_AUDIT_SOURCE = "/services/compliance"


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
    trace_id, _ = current_trace_ids()
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
        **audit_log_fields(),
    )
    await try_publish_audit_event(
        service_source=COMPLIANCE_AUDIT_SOURCE,
        organization_id=organization_id,
        action=action,
        actor_user_id=actor_user_id,
        resource_type=entity_type,
        resource_id=entity_id,
        message=detail,
        trace_id=trace_id,
    )
