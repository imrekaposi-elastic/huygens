# Huygens architecture

Architecture decisions, diagrams, and contracts for the Huygens platform.

## Documents

| Path | Description |
|------|-------------|
| [erd/tenancy.md](erd/tenancy.md) | Multi-tenant data model |
| [adrs/](adrs/) | Architecture Decision Records (ADRs) |
| [../install/air-gapped.md](../install/air-gapped.md) | Offline / air-gapped installation |
| [diagrams/](diagrams/) | Excalidraw diagrams (import into [excalidraw.com](https://excalidraw.com)) |

## ADR index

| ADR | Title |
|-----|--------|
| [0001](adrs/0001-monorepo-and-open-source.md) | Monorepo layout and Apache 2.0 |
| [0002](adrs/0002-tenancy-and-projects.md) | Tenancy: organization, project, resources |
| [0003](adrs/0003-postgresql-and-elasticsearch.md) | PostgreSQL vs Elasticsearch ECS |
| [0004](adrs/0004-kafka-event-bus.md) | Kafka topics and event envelope |
| [0005](adrs/0005-agent-token-vault.md) | Agent token vault and platform_admin |
| [0006](adrs/0006-libvirt-dual-io.md) | Libvirt write queue and read path |
| [0007](adrs/0007-readonly-system-networks.md) | Readonly libvirt `default` network |
| [0008](adrs/0008-opentelemetry-and-edot.md) | OpenTelemetry and EDOT-friendly export |
| [0009](adrs/0009-air-gapped-install.md) | Air-gapped installation |
| [0010](adrs/0010-know-why-and-asset-criticality.md) | Know why: compliance and asset criticality |
| [0011](adrs/0011-sse-auth-via-authorization-header.md) | SSE: Bearer header only; no `EventSource ?token=` |
| [0011](adrs/0011-keycloak-group-role-mapping.md) | Keycloak SSO and IdP group → role mapping |
| [0012](adrs/0012-hybrid-breakout-and-network-linking.md) | Phase 6: hybrid breakout, network links, topology |

## Phase map

See [../PHASED_PLAN.md](../PHASED_PLAN.md) for delivery phases 0–17.

**Projects service** (`services/projects`, port 8084) is the operator-facing control-plane API: project CRUD, RBAC, and proxied libvirt agent mutations. It appears on [diagrams/01-system-context.excalidraw](diagrams/01-system-context.excalidraw) and related deployment/tenancy drawings.

**Web console** (`web/`, Phase 5 ✅) proxies to IAM, projects, inventory, and registry via nginx in Compose. Live inventory uses **Kafka → inventory SSE hub → console** ([ADR 0011](adrs/0011-sse-auth-via-authorization-header.md)).

**Phase 6 (network linking):** `projects` + `breakout-controller` + topology UI in Compose; libvirt agent on each hypervisor. Operational release and validation: [operations/phase6-release-and-validation.md](../operations/phase6-release-and-validation.md).

**Elasticsearch** is part of the target architecture for **audit logs (ECS)**, compliance dashboards, and **SSH session recording search** (Phase 9). Events flow **Kafka → ES ingest**; PostgreSQL stays the system of record. Inventory publishes snapshots via **`shared/huy_events`**; link lifecycle publishes to **`huy.network.links`**; agent→Kafka publish remains partial — see [adrs/0004-kafka-event-bus.md](adrs/0004-kafka-event-bus.md).
