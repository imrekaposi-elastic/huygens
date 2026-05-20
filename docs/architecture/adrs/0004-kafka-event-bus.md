# ADR 0004: Kafka event bus

## Status

Accepted (Phase 0); amended Phase 5 prep (Kafka required in default stack)

## Context

Event-driven architecture for inventory updates, audit fan-out, and console live views.

## Decision

- **Apache Kafka** as the event backbone (not NATS).
- **Standard deployment:** Kafka runs alongside PostgreSQL in local Compose, Helm, and production. Control-plane services start only after both are healthy.
- **`KAFKA_BOOTSTRAP`** — primary configuration for broker addresses (comma-separated list for clusters, e.g. `kafka-1:9092,kafka-2:9092`). Compose default: `kafka:9092`. Optional **`KAFKA_CLIENT_ID`** per service.
- **Shared client:** [`shared/huy_events`](../../../shared/huy_events) (`huy-events` package) — CloudEvents envelope builder, topic constants, `aiokafka` producer and broadcast consumer helpers. Services must not duplicate Kafka client code.
- Topics (v1):

| Topic | Producer | Consumer |
|-------|----------|----------|
| `huy.agent.events` | Agents | Registry, inventory, console |
| `huy.inventory.snapshots` | Inventory poller | Registry DB, console (SSE via broadcast consumer) |
| `huy.audit.events` | All services | ES ingest (audit-ingest / Logstash) |

- Payload: **CloudEvents 1.0** envelope + JSON `data` (schemas in `schemas/kafka/`).
- Inventory poller **publishes** successful snapshots to `huy.inventory.snapshots` when `KAFKA_PUBLISH_ENABLED=true` (default in Compose).
- **Elasticsearch** is the long-term search and analytics store for **audit ECS**, **compliance views**, and **SSH gateway session recordings** (Phase 9) — not a disposable sidecar. PostgreSQL remains system of record; ES is the query plane at scale.

### Degraded mode (air-gap exception)

Explicit operator choice only: poll-only inventory without Kafka publish, audit retained in PostgreSQL until ES is available. **Not** the default `docker compose up` stack.

## Consequences

- Schema changes require version bump in `dataschema` URI or `data` version field.
- Multi-replica inventory SSE uses **broadcast consumer groups** (unique `group.id` per pod), not a single load-balanced group.
- SSE authentication: [ADR 0011](0011-sse-auth-via-authorization-header.md) — `Authorization: Bearer` only; reject `?token=`; console uses fetch-based SSE, not `EventSource`.
- Console and SOC workflows query ES (Kibana optional pack) for “who did what” and session replay metadata.
