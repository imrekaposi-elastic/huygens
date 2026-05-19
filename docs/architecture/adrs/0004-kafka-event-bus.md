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
| `huy.audit.events` | All services | ES ingest |

- Payload: **CloudEvents 1.0** envelope + JSON `data` (schemas in `schemas/kafka/`).
- Phase 1 MVP may poll HTTP only; Kafka publish optional until Phase 1+.

## Consequences

- Schema changes require version bump in `dataschema` URI or `data` version field.
- Air-gapped: Kafka cluster on-site or degraded mode without events (poll only).
