# ADR 0007: Readonly system networks

## Status

Accepted (Phase 0)

## Context

Libvirt `default` network on hosts is infrastructure; operators should not delete it via console.

## Decision

- Agent API exposes `readonly: true` and `deletable: false` on network objects for system names (`default` minimum).
- Control plane inventory preserves flags; proxy rejects DELETE on readonly networks.
- GUI (Phase 5): no delete control; tooltip "system network".

## Consequences

- Project workloads use IPAM-assigned vnets (`lab0`, etc.), not management of host `default`.
