"""Registry audit events (Kafka + structlog)."""

from __future__ import annotations

import structlog
from huy_events import PLATFORM_AUDIT_ORG_ID, try_publish_audit_event
from huy_telemetry.context import audit_log_fields, current_trace_ids

logger = structlog.get_logger(__name__)
REGISTRY_AUDIT_SOURCE = "/services/registry"


async def record_audit(
    *,
    organization_id: str,
    actor_user_id: str,
    action: str,
    resource_type: str | None = None,
    resource_id: str | None = None,
    message: str | None = None,
    outcome: str = "success",
    labels: dict[str, str] | None = None,
) -> None:
    trace_id, _ = current_trace_ids()
    logger.info(
        "registry_audit",
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        message=message,
        outcome=outcome,
        labels=labels,
        **audit_log_fields(),
    )
    await try_publish_audit_event(
        service_source=REGISTRY_AUDIT_SOURCE,
        organization_id=organization_id,
        action=action,
        outcome=outcome,
        actor_user_id=actor_user_id,
        resource_type=resource_type,
        resource_id=resource_id,
        message=message,
        trace_id=trace_id,
        labels=labels,
    )


async def record_platform_audit(
    *,
    actor_user_id: str,
    action: str,
    resource_type: str | None = None,
    resource_id: str | None = None,
    message: str | None = None,
    outcome: str = "success",
    labels: dict[str, str] | None = None,
) -> None:
    await record_audit(
        organization_id=PLATFORM_AUDIT_ORG_ID,
        actor_user_id=actor_user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        message=message,
        outcome=outcome,
        labels=labels,
    )
