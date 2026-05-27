# Phase 7 — compliance and lifecycle guards

Operational guide for **org compliance** (`services/compliance`, port **8086**) and **deletion guards** added to the projects service. Complements [ADR 0010](../architecture/adrs/0010-know-why-and-asset-criticality.md) and [PHASED_PLAN.md](../PHASED_PLAN.md) Phase 7.

## What shipped (MVP)

| Area | Console | API / service |
|------|---------|----------------|
| Org catalog & checks | **Compliance** → Catalog, Checks | `huy-compliance` |
| Explorer | **Compliance** → Explorer | Filters by catalog, traits, resource type; pagination |
| Asset criticality | Project tab, VM/network dialogs | Direct assignment per resource |
| Infrastructure standards | **Infrastructure** → provider / region tree | Catalog checkboxes on provider and each region |
| Placement rationale | VM **Why here?** | `GET .../placement-rationale` |
| Project aggregate compliance | Blue membership on project tab / explorer | Intersection of all child VMs + networks |
| Network delete guard | **Projects** → Networks | HTTP **409** when blocked |
| IP pool delete | **IPAM** → Delete pool | HTTP **409** when blocked |

Rebuild after pulling changes:

```bash
docker compose up -d --build compliance projects registry web
```

The console nginx (and Vite dev proxy) route `/api/v1/organizations/{org_id}/compliance*` to `compliance:8086`.

## Compliance membership (green / grey / blue)

| Color | Meaning | Editable? |
|-------|---------|-----------|
| **Green** | Direct assignment on this resource (project, VM, or network) | Yes (`compliance_engineer` / `admin`) |
| **Grey** | Inherited from **provider** or **region** placement (catalog standards on infrastructure profiles) | No — change infrastructure or move the agent |
| **Blue** | **Project only:** every VM and network in the project satisfies this catalog standard (direct or inherited) | No — derived; fix workloads until all comply |

A project shows **Data:EU** in blue only when **each** VM and network in that project has Data:EU in its effective compliance (direct + placement inherited).

## Infrastructure compliance inheritance

Standards are org **catalog items** linked to:

1. **Provider** — applies to all agents on that provider.
2. **Region** — applies to agents placed in that region **or any sub-region** (parent chain walked via registry `parent_region_id`).

Region standards on **Falkenstein** flow to agents in child regions (e.g. **FS6**) without re-saving on the child node.

Configure under **Infrastructure** (platform admin): expand a provider or region in the tree → **Region compliance standards** / **Provider compliance** panel → check catalog items → **Save standards**.

Roles: `admin` and `compliance_admin` can edit infrastructure compliance; `compliance_engineer` assigns per-resource criticality.

### Traits API vs catalog profiles

The compliance service still exposes **free-form trait** CRUD (`provider_traits`, `region_traits` tables). The console and placement inheritance use **catalog item links** on infrastructure profiles (`InfrastructureProviderCompliance`, `RegionComplianceItemLink`). Explorer “trait” filters match catalog-derived `TraitSummary` slugs, not the legacy trait rows.

## Compliance operator workflow

1. **Catalog** — define standards (name, slug, MoSCoW).
2. **Infrastructure** — attach standards to provider and/or region nodes (grey inheritance).
3. **Projects** — optional direct project standards (green); blue appears when all children align.
4. **VMs / networks** — per-resource direct assignment or rely on grey inheritance.
5. **Explorer** — find gaps (e.g. missing BIO, missing EU trait); presets on Overview.
6. **Checks** — owners and validity periods (alerter logs to structlog today; ES notifications deferred).

## Network delete checklist

`DELETE /api/v1/projects/{project_id}/agents/{agent_id}/networks/{name}` returns **409** when:

| Blocker | Action |
|---------|--------|
| VMs use this network | Delete or reconfigure VMs (`network` field on agent) |
| Topology link references this vnet | Remove link in **Topology** first |
| Breakout active (WireGuard or flat enabled) | Disable breakout on the network |

Readonly networks (`default`, `readonly: true`) still return **403**.

The API **does not** auto-delete topology links when deleting a network — remove links explicitly.

## IP pool delete checklist

`DELETE /api/v1/organizations/{org_id}/ipam/pools/{pool_id}` returns **409** when:

| Pool kind | Blocker |
|-----------|---------|
| **vnet** | Any `reserved` or `allocated` subnet assignment in the pool |
| **overlay** | Any active topology link using this pool as `overlay_pool_id` |

Empty pools (no assignments, no links) delete successfully from **IPAM**.

## Known gaps (documented backlog)

- **Placement `config_drift`** — API field exists; not populated from inventory yet.
- **Check alerter** — periodic scan logs expiring checks; no email/ES notification.
- **Kibana pack** — spike only ([compliance/kibana/README.md](../compliance/kibana/README.md)).
- **Free-form traits** — REST API without console UI.

## Related docs

- [ADR 0010](../architecture/adrs/0010-know-why-and-asset-criticality.md)
- [services/compliance/README.md](../../services/compliance/README.md)
- [services/projects/README.md](../../services/projects/README.md) — delete guards
- [phase6-release-and-validation.md](phase6-release-and-validation.md) — topology and breakout
