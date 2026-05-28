"""Shared Kafka and CloudEvents helpers for Huygens control plane."""

from huy_events.audit_publish import (
    AUDIT_DATASCHEMA,
    AUDIT_EVENT_TYPE,
    PLATFORM_AUDIT_ORG_ID,
    build_audit_data,
    publish_audit_event,
    try_publish_audit_event,
)
from huy_events.kafka_lifecycle import start_audit_kafka_producer, stop_audit_kafka_producer
from huy_events.audit_registry import configure_audit_publisher, get_audit_publisher
from huy_events.cloudevents import build_envelope
from huy_events.config import KafkaSettings, parse_bootstrap_servers
from huy_events.consumer import HuyBroadcastConsumer
from huy_events.producer import HuyKafkaProducer
from huy_events.topics import (
    TOPIC_AGENT_EVENTS,
    TOPIC_AUDIT_EVENTS,
    TOPIC_INVENTORY_SNAPSHOTS,
    TOPIC_NETWORK_LINKS,
)

__all__ = [
    "AUDIT_DATASCHEMA",
    "AUDIT_EVENT_TYPE",
    "PLATFORM_AUDIT_ORG_ID",
    "HuyBroadcastConsumer",
    "HuyKafkaProducer",
    "KafkaSettings",
    "TOPIC_AGENT_EVENTS",
    "TOPIC_AUDIT_EVENTS",
    "TOPIC_INVENTORY_SNAPSHOTS",
    "TOPIC_NETWORK_LINKS",
    "build_audit_data",
    "build_envelope",
    "configure_audit_publisher",
    "get_audit_publisher",
    "parse_bootstrap_servers",
    "publish_audit_event",
    "start_audit_kafka_producer",
    "stop_audit_kafka_producer",
    "try_publish_audit_event",
]
