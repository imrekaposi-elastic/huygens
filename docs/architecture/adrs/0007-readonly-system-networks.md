# ADR 0007: Readonly system networks

## Status

Accepted (Phase 0)

## Context

Libvirt `default` network on hosts is infrastructure; operators should not delete it via console.

## Decision

- Agent API exposes `readonly: true` and `deletable: false` on network objects for system names (`default` minimum).
- Control plane inventory preserves flags; proxy rejects DELETE on readonly networks.
- GUI (Phase 5 ✅): no delete control; readonly badge; `default` hidden from project network list.

### Deletion preconditions (managed vnets)

Readonly applies to system networks only. For normal project vnets, `projects` returns **409** before agent delete when VMs, topology links, or active breakout still reference the network. See [phase7 operations](../../operations/phase7-compliance-and-lifecycle-guards.md).

## Consequences

- Project workloads use IPAM-assigned vnets (`lab0`, etc.), not management of host `default`.
