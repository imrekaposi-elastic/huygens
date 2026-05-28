# ADR 0010: Know why and asset criticality

## Status

Accepted (Phase 0); **MVP + GRC extensions implemented** in Phase 7 (`huy-compliance`, console)

## Context

Strategic goal: *know where workloads run and why*. FRAMEWORK_PLAN adds `compliance_engineer` and asset criticality from an org compliance catalog.

## Decision

**Where:** provider → region (tree) → agent → project → VM / network (inventory + UI).

**Why** (explainability and membership):

1. **Infrastructure compliance profiles** — org catalog items linked to a **provider** and/or **region**. Region links apply to agents in that region and **descendant sub-regions** (walk `parent_region_id` via registry).
2. **Direct asset criticality** — `compliance_engineer` assigns catalog items to project / VM / network.
3. **Project aggregate** — a catalog item appears on a project only when **every** VM and network in the project has that item in effective compliance (direct ∪ placement inherited).
4. Optional **placement note** (free text, audited) on resource assignments.

`GET /api/v1/organizations/{org_id}/resources/{resource_type}/placement-rationale?project_id=...&agent_id=...&name=...` returns structured JSON for the console.

**Compliance explorer** filters workloads by effective catalog membership and placement trait slugs (catalog items plus **qualitative characteristics** linked on providers/regions).

### Qualitative characteristics (Phase 7+)

Org-defined characteristics (`/qualitative-characteristics`) replace free-form traits for console and inheritance. Link on provider/region via `/characteristics` endpoints; Explorer facets expose name, slug, and MoSCoW.

### Legacy traits API (deprecated)

`provider_traits` / `region_traits` REST **writes return 410**; GET remains for migration only (`Deprecation` header). Use `POST .../qualitative-characteristics/migrate-from-legacy-traits` to copy legacy rows into characteristics + links.

## Consequences

- PostgreSQL: `org_compliance_items`, `asset_criticality_assignments`, `infrastructure_provider_compliance` (+ item links), `region_compliance_item_links`, optional `provider_traits` / `region_traits`.
- Registry internal: flat region list with `parent_region_id` for compliance lineage (service token).
- Elasticsearch: compliance search views and audit (deferred for dashboards); PG is source of truth for assignments.
- `config_drift` on placement rationale reserved for inventory integration (not yet populated).

## References

- [Phase 7 operations](../../operations/phase7-compliance-and-lifecycle-guards.md)
- [services/compliance/README.md](../../../services/compliance/README.md)
