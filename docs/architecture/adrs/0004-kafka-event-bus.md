# ADR 0004: Kafka event bus

## Status

Accepted (Phase 0)

## Context

Event-driven architecture for inventory updates, audit fan-out, and console live views.

## Decision

- **Apache Kafka** as the event backbone (not NATS).
- Topics (v1):

| Topic | Producer | Consumer |
|-------|----------|----------|
| `huy.agent.events` | Agents | Registry, inventory, console |
| `huy.inventory.snapshots` | Inventory poller | Registry DB, console |
| `huy.audit.events` | All services | ES ingest (audit-ingest / Logstash) |

- Payload: **CloudEvents 1.0** envelope + JSON `data` (schemas in `schemas/kafka/`).
- Phase 1 MVP may poll HTTP only; Kafka publish optional until Phase 1+.
- **Elasticsearch** is the long-term search and analytics store for **audit ECS**, **compliance views**, and **SSH gateway session recordings** (Phase 9) — not a disposable sidecar. PostgreSQL remains system of record; ES is the query plane at scale.

## Consequences

- Schema changes require version bump in `dataschema` URI or `data` version field.
- Air-gapped: Kafka + ES on-site, or degraded mode (poll-only inventory; audit retained in PG until ES available).
- Console and SOC workflows query ES (Kibana optional pack) for “who did what” and session replay metadata.
