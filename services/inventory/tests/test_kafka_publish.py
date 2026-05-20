"""Kafka snapshot publish tests."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
import respx
from httpx import Response

from huy_events import TOPIC_INVENTORY_SNAPSHOTS
from huy_inventory.config import get_settings
from huy_inventory.db import get_engine, get_session_factory, init_db
from huy_inventory.models import Base
from huy_inventory.services.poller_loop import InventoryPoller
from huy_inventory.services.snapshot_publish import kafka_event_data, publish_inventory_snapshot


def test_kafka_event_data_strips_agent_blob() -> None:
    payload = {
        "version": 1,
        "agent_id": "a",
        "organization_id": "o",
        "region_id": "r",
        "polled_at": "2026-01-01T00:00:00+00:00",
        "agent": {"hostname": "hv1"},
        "vms": [],
        "networks": [{"name": "default"}],
        "config_drift": False,
    }
    data = kafka_event_data(payload)
    assert "agent" not in data
    assert data["networks"][0]["name"] == "default"


@pytest.mark.asyncio
async def test_publish_inventory_snapshot_calls_producer() -> None:
    producer = MagicMock()
    producer.send = AsyncMock()
    payload = {
        "version": 1,
        "agent_id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
        "organization_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        "region_id": "cccccccc-cccc-cccc-cccc-cccccccccccc",
        "polled_at": datetime.now(UTC).isoformat(),
        "vms": [],
        "networks": [],
        "config_drift": False,
    }
    await publish_inventory_snapshot(producer, payload)
    producer.send.assert_awaited_once()
    call = producer.send.await_args
    assert call.args[0] == TOPIC_INVENTORY_SNAPSHOTS
    envelope = call.args[1]
    assert envelope["type"] == "com.huygens.inventory.snapshot.v1"
    assert envelope["data"]["agent_id"] == payload["agent_id"]


@respx.mock
@pytest.mark.asyncio
async def test_poller_publishes_after_successful_poll() -> None:
    get_settings.cache_clear()
    settings = get_settings()
    org_id = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    agent_id = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
    base = "https://agent.test"

    respx.get(f"{settings.registry_url}/api/v1/internal/poll-targets").mock(
        return_value=Response(
            200,
            json=[
                {
                    "agent_id": agent_id,
                    "organization_id": org_id,
                    "region_id": "cccccccc-cccc-cccc-cccc-cccccccccccc",
                    "base_url": base,
                    "agent_token": "secret",
                    "refresh_seconds": 30,
                    "tls_verify": False,
                }
            ],
        )
    )
    respx.patch(f"{settings.registry_url}/api/v1/internal/agents/{agent_id}/poll-status").mock(
        return_value=Response(204)
    )
    respx.get(f"{base}/api/v1/agent").mock(return_value=Response(200, json={"hostname": "hv1"}))
    respx.get(f"{base}/api/v1/vms").mock(return_value=Response(200, json=[]))
    respx.get(f"{base}/api/v1/networks").mock(return_value=Response(200, json=[]))

    init_db(settings)
    async with get_engine().begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    mock_producer = MagicMock()
    mock_producer.send = AsyncMock()
    poller = InventoryPoller(settings, get_session_factory(), kafka_producer=mock_producer)
    await poller.poll_once()
    mock_producer.send.assert_awaited_once()
