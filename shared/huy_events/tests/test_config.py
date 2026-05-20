"""huy-events unit tests."""

from __future__ import annotations

import pytest

from huy_events.cloudevents import build_envelope
from huy_events.config import parse_bootstrap_servers


def test_parse_bootstrap_servers_single() -> None:
    assert parse_bootstrap_servers("kafka:9092") == ["kafka:9092"]


def test_parse_bootstrap_servers_cluster() -> None:
    assert parse_bootstrap_servers("kafka-1:9092, kafka-2:9092 ") == [
        "kafka-1:9092",
        "kafka-2:9092",
    ]


def test_parse_bootstrap_servers_empty_raises() -> None:
    with pytest.raises(ValueError, match="KAFKA_BOOTSTRAP"):
        parse_bootstrap_servers("  , ")


def test_build_envelope() -> None:
    env = build_envelope(
        event_type="com.huygens.inventory.snapshot.v1",
        source="/inventory/poller",
        data={"version": 1, "agent_id": "a"},
        subject="agent-a",
    )
    assert env["specversion"] == "1.0"
    assert env["type"] == "com.huygens.inventory.snapshot.v1"
    assert env["data"]["agent_id"] == "a"
    assert env["subject"] == "agent-a"
