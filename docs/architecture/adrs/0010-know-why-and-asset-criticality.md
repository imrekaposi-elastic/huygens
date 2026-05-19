# ADR 0010: Know why and asset criticality

## Status

Accepted (Phase 0); implementation Phase 7

## Context

Strategic goal: *know where workloads run and why*. FRAMEWORK_PLAN adds `compliance_engineer` and asset criticality from org compliance catalog.

## Decision

**Where:** provider → region → agent → project → VM (inventory + UI).

**Why** (explainability API, Phase 7):

1. **Inherited traits** from provider and region (sovereignty, BIO, MoSCoW qualifications).
2. **Asset criticality** — `compliance_engineer` assigns org compliance items to VM/project/vnet.
3. Optional **placement note** (free text, audited) for human rationale.

`GET /resources/{type}/{id}/placement-rationale` returns structured JSON for console and Kibana compliance app.

## Consequences

- PostgreSQL: `org_compliance_items`, `asset_criticality_assignments`, `provider_traits`, `region_traits`.
- Elasticsearch: compliance search views and audit; not source of truth for assignments.
