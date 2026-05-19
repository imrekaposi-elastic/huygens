# ADR 0003: PostgreSQL and Elasticsearch

## Status

Accepted (Phase 0)

## Context

Need transactional config (orgs, RBAC, desired state) and searchable audit/compliance views at scale.

## Decision

| Store | Use |
|-------|-----|
| **PostgreSQL** | System of record: users, roles, providers, regions, agents, projects, desired state, token hashes, IPAM |
| **Elasticsearch (ECS)** | Audit logs, compliance search views, SSH session logs (later), dashboards |
| **Metrics TS** | Prometheus scrape from agents; optional Elasticsearch data streams via EDOT |

Do **not** use Elasticsearch as authoritative RBAC or billing source.

## Consequences

- `audit-ingest` service or pipeline writes ECS documents to ES.
- Compliance Kibana app (Phase 7/8) reads ES indices, not PG replicas.
- Air-gapped installs: BYO Elasticsearch or run without ES (audit buffered to files until available).
