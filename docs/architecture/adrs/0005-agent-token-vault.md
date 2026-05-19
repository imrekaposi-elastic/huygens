# ADR 0005: Agent token vault

## Status

Accepted (Phase 0)

## Context

Agents authenticate with bearer tokens. Only platform operators may provision hosts.

## Decision

- One bearer token per agent, generated at registration.
- Store **bcrypt/argon2 hash** in PostgreSQL; never log plaintext.
- **`platform_admin`** is the only role that can export token once for OOB host setup.
- **Org admin** cannot register agents, connect hypervisors, or view tokens.
- `platform_admin` assigns `organization_id`, `provider_id`, `region_id` at registration.

## Consequences

- Registry API: `POST /agents` (platform_admin), `POST /agents/{id}/export-token` (platform_admin, one-time).
- Rotation: platform_admin only; old token invalidated immediately.
