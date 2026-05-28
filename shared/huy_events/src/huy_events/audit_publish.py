"""Publish ECS-aligned audit events to huy.audit.events (CloudEvents envelope)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import structlog

from huy_events.audit_registry import get_audit_publisher
from huy_events.cloudevents import build_envelope
from huy_events.producer import HuyKafkaProducer
from huy_events.topics import TOPIC_AUDIT_EVENTS

logger = structlog.get_logger(__name__)

AUDIT_EVENT_TYPE = "com.huygens.audit.v1"
AUDIT_DATASCHEMA = "https://huygens.dev/schemas/kafka/audit-event.schema.json"
# Platform-scoped actions (global registry catalog, platform IdP mappings) without a tenant org.
PLATFORM_AUDIT_ORG_ID = "00000000-0000-0000-0000-000000000001"


def build_audit_data(
    *,
    organization_id: str,
    action: str,
    outcome: str = "success",
    actor_user_id: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    resource_name: str | None = None,
    message: str | None = None,
    trace_id: str | None = None,
    labels: dict[str, str] | None = None,
) -> dict[str, Any]:
    data: dict[str, Any] = {
        "version": 1,
        "organization_id": organization_id,
        "action": action,
        "outcome": outcome,
        "timestamp": datetime.now(UTC).isoformat(),
    }
    if actor_user_id is not None:
        data["user_id"] = actor_user_id
        data["user"] = {"id": actor_user_id}
    if resource_type is not None or resource_id is not None or resource_name is not None:
        resource: dict[str, Any] = {}
        if resource_type is not None:
            resource["type"] = resource_type
        if resource_id is not None:
            resource["id"] = resource_id
        if resource_name is not None:
            resource["name"] = resource_name
        data["resource"] = resource
    if message is not None:
        data["message"] = message
    if trace_id is not None:
        data["trace_id"] = trace_id
    if labels:
        data["labels"] = labels
    return data


async def publish_audit_event(
    producer: HuyKafkaProducer,
    *,
    service_source: str,
    organization_id: str,
    action: str,
    outcome: str = "success",
    actor_user_id: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    resource_name: str | None = None,
    message: str | None = None,
    trace_id: str | None = None,
    labels: dict[str, str] | None = None,
) -> None:
    data = build_audit_data(
        organization_id=organization_id,
        action=action,
        outcome=outcome,
        actor_user_id=actor_user_id,
        resource_type=resource_type,
        resource_id=resource_id,
        resource_name=resource_name,
        message=message,
        trace_id=trace_id,
        labels=labels,
    )
    subject = resource_id or organization_id
    envelope = build_envelope(
        event_type=AUDIT_EVENT_TYPE,
        source=service_source,
        data=data,
        subject=subject,
        dataschema=AUDIT_DATASCHEMA,
    )
    await producer.send(TOPIC_AUDIT_EVENTS, envelope, key=organization_id)
    logger.debug(
        "audit_event_published",
        action=action,
        organization_id=organization_id,
        resource_type=resource_type,
        resource_id=resource_id,
    )


async def try_publish_audit_event(
    *,
    service_source: str,
    organization_id: str,
    action: str,
    outcome: str = "success",
    actor_user_id: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    resource_name: str | None = None,
    message: str | None = None,
    trace_id: str | None = None,
    labels: dict[str, str] | None = None,
) -> None:
    """Best-effort publish using the process-wide producer; never raises."""
    producer = get_audit_publisher()
    if producer is None:
        return
    try:
        await publish_audit_event(
            producer,
            service_source=service_source,
            organization_id=organization_id,
            action=action,
            outcome=outcome,
            actor_user_id=actor_user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_name=resource_name,
            message=message,
            trace_id=trace_id,
            labels=labels,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "audit_event_publish_failed",
            action=action,
            organization_id=organization_id,
            error=str(exc),
        )
