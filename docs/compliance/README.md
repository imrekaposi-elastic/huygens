# Compliance (Phase 7+)

Huygens compliance is split into two complementary layers:

## Layer 1: Placement compliance (Phase 7 MVP)

- **Org catalog items**: simple standards (BIO, ISO, “Data:EU”, …)
- **Infrastructure inheritance**: attach catalog items to **provider** and **region** (region tree inherits to sub-regions)
- **Criticality assignments**: direct catalog items on project / VM / network
- **Explorer**: find “missing” coverage and understand inherited posture (green/grey/blue membership)

Source of truth: PostgreSQL in `huy-compliance`.

## Layer 2: GRC primitives (Phase 7+ extensions)

Adds audit-ready structures:

- **Compliance standards**: top-level named standards (e.g. “ISO 27001:2022”)
- **Controls**: sub-items under a standard (name, description, rationale, optional control code)
- **Cycles**: repeated review/assessment windows for a standard
- **Evidence**: uploaded per control (categorized as design / implementation / operating effectiveness)
- **Packs**: importable JSON bundles to seed standards/controls
- **PDF export**: request from the GRC console; the browser polls until ready and downloads once (generated time and requester are embedded in the PDF)
- **Qualitative characteristics**: org-defined labels (name, description, MoSCoW, kind) linked on providers/regions in Infrastructure; inherited to workloads and Explorer trait filters. Legacy free-form traits are deprecated — use **Migrate legacy traits** in GRC when upgrading.

Console entry point: **Compliance → GRC**.

## Storage and audit

- **Evidence bytes** are stored in an object store; the database stores references (object key, hash, size, metadata).
- **Audit** events are recorded transactionally in PostgreSQL and emitted as structured logs (`compliance_audit`).

## Phase 7 sign-off scope

**In scope (shipped):** Layer 1 placement MVP + Layer 2 GRC increments (standards through qualitative characteristics). See [PHASED_PLAN.md](../PHASED_PLAN.md) Phase 7 and [operations guide](../operations/phase7-compliance-and-lifecycle-guards.md).

**Out of scope / backlog:** GRC pie-chart dashboard, Explorer filters for evidence/cycle gaps, `config_drift` from inventory, Kibana product dashboards, bundled ISO/BIO pack artifacts in-repo.

## See also

- [Phase 7 operations guide](../operations/phase7-compliance-and-lifecycle-guards.md)
- [Compliance packs](packs.md)
- [Kibana pack spike](./kibana/README.md)
