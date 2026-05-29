#!/usr/bin/env bash
# Create Huygens application Kafka topics (idempotent).
# Keep topic names in sync with shared/huy_events/src/huy_events/topics.py and ADR 0004.
set -euo pipefail

BOOTSTRAP="${KAFKA_BOOTSTRAP:-kafka:9092}"
PARTITIONS="${KAFKA_TOPIC_PARTITIONS:-1}"
REPLICATION="${KAFKA_TOPIC_REPLICATION_FACTOR:-1}"

TOPICS=(
  huy.agent.events
  huy.inventory.snapshots
  huy.audit.events
  huy.network.links
  huy.session.events
  huy.session.recording
)

echo "Ensuring Kafka topics on ${BOOTSTRAP} (partitions=${PARTITIONS}, replication=${REPLICATION})"

for topic in "${TOPICS[@]}"; do
  /opt/kafka/bin/kafka-topics.sh \
    --bootstrap-server "${BOOTSTRAP}" \
    --create \
    --if-not-exists \
    --topic "${topic}" \
    --partitions "${PARTITIONS}" \
    --replication-factor "${REPLICATION}"
  echo "  ok: ${topic}"
done

echo "Kafka topic init complete."
