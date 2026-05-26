# ADR 0001: Monorepo layout and open source

## Status

Accepted (Phase 0)

## Context

Huygens is an open-source infrastructure operations platform (see strategic proposal).
Components include hypervisor agents, control-plane microservices, web console, and shared contracts.

## Decision

- Single monorepo at repository root.
- **Apache License 2.0** for all first-party code (aligns with Elastic client/integration OSS).
- Layout:

```
agents/          # Hypervisor agents (libvirt today)
services/        # Control plane microservices
web/             # Console SPA (Phase 5 ✅)
schemas/         # Kafka and shared JSON schemas
docs/            # Architecture, install guides
```

- OSPO/Legal sign-off required before public announcement if affiliated with Elastic.

## Consequences

- One PR can span agent + control plane when contracts change.
- Each component keeps its own `pyproject.toml` and README.
- GPL v3 root license replaced by Apache 2.0 in Phase 0.
