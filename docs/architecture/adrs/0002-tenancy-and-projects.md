# ADR 0002: Tenancy and projects

## Status

Accepted (Phase 0)

## Context

Multi-tenant SaaS: many organizations, each with projects, VMs, and hypervisor agents.

## Decision

- **Organization** is the tenant root.
- **Project** is a container for 1+ virtual networks, VMs, cloud-init profiles, and quotas — not 1:1 with a single vnet.
- **Provider → Region → Agent** models where hypervisors run; agent bound to one organization at registration.
- Inventory and RBAC always filter by `organization_id` except for `platform_admin`.

See [../erd/tenancy.md](../erd/tenancy.md).

## Consequences

- Phase 1 registry tables include `organization_id` on all agent rows.
- Phase 3 project service owns project CRUD and agent proxy scope.
