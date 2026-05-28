"""Audit CloudEvents publish helpers."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from huy_events.audit_publish import (
    AUDIT_EVENT_TYPE,
    build_audit_data,
    publish_audit_event,
    try_publish_audit_event,
)
from huy_events.audit_registry import configure_audit_publisher
from huy_events.topics import TOPIC_AUDIT_EVENTS


def test_build_audit_data_required_fields() -> None:
    data = build_audit_data(
        organization_id="org-1",
        action="compliance.catalog.create",
        actor_user_id="user-1",
        resource_type="compliance_standard",
        resource_id="std-1",
        message="Created standard",
    )
    assert data["version"] == 1
    assert data["organization_id"] == "org-1"
    assert data["action"] == "compliance.catalog.create"
    assert data["outcome"] == "success"
    assert data["user_id"] == "user-1"
    assert data["resource"]["type"] == "compliance_standard"
    assert data["resource"]["id"] == "std-1"
    assert data["message"] == "Created standard"
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_publish_audit_event_sends_cloudevent() -> None:
    producer = AsyncMock()
    await publish_audit_event(
        producer,
        service_source="/services/compliance",
        organization_id="org-1",
        action="evidence.upload",
        actor_user_id="user-1",
        resource_type="control_evidence",
        resource_id="ev-1",
    )
    producer.send.assert_awaited_once()
    call = producer.send.await_args
    topic = call.args[0]
    envelope = call.args[1]
    key = call.kwargs.get("key") or (call.args[2] if len(call.args) > 2 else None)
    assert topic == TOPIC_AUDIT_EVENTS
    assert key == "org-1"
    assert envelope["type"] == AUDIT_EVENT_TYPE
    assert envelope["source"] == "/services/compliance"
    assert envelope["data"]["organization_id"] == "org-1"
    assert envelope["data"]["action"] == "evidence.upload"


@pytest.mark.asyncio
async def test_try_publish_audit_event_no_producer() -> None:
    configure_audit_publisher(None)
    await try_publish_audit_event(
        service_source="/services/iam",
        organization_id="org-1",
        action="org.create",
    )


@pytest.mark.asyncio
async def test_try_publish_audit_event_swallows_errors() -> None:
    producer = AsyncMock()
    producer.send.side_effect = RuntimeError("broker down")
    configure_audit_publisher(producer)
    await try_publish_audit_event(
        service_source="/services/registry",
        organization_id="org-1",
        action="agent.create",
    )
    configure_audit_publisher(None)
