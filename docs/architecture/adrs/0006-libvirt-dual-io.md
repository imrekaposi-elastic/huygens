# ADR 0006: Libvirt dual I/O

## Status

Accepted (Phase 0); partial implementation in agent (Phase 1b)

## Context

A single-threaded libvirt queue caused `GET /networks` and health checks to hang when status monitor blocked on guest-agent `interfaceAddresses`.

## Decision

| Path | Operations |
|------|------------|
| **Write queue** | define, create, destroy, undefine, network start/stop — serialized |
| **Read path** | list_*, domain_state, metrics — must not wait behind write queue |

Phase 1b interim: async FastAPI routes + DHCP-lease-only for guest IP (no qemu-ga blocking).

Future: dedicated read connection pool or `list_*` endpoints that bypass write queue entirely.

## Consequences

- Control-plane poller uses read-path APIs only.
- Prometheus scrape must not block VM mutations.
