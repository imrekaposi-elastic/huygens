# Phase 7 — compliance and lifecycle guards

Operational guide for **org compliance** (`services/compliance`, port **8086**) and **deletion guards** added to the projects service. Complements [ADR 0010](../architecture/adrs/0010-know-why-and-asset-criticality.md) and [PHASED_PLAN.md](../PHASED_PLAN.md) Phase 7.

## What shipped (placement MVP)

| Area | Console | API / service |
|------|---------|----------------|
| Org catalog & checks | **Compliance** → Catalog, Checks | `huy-compliance` |
| Explorer | **Compliance** → Explorer | Filters by catalog, traits, resource type; pagination |
| Asset criticality | Project tab, VM/network dialogs | Direct assignment per resource |
| Infrastructure standards | **Infrastructure** → provider / region tree | Catalog checkboxes on provider and each region |
| Qualitative characteristics | **Compliance** → GRC; link on **Infrastructure** | Provider/region `/characteristics` |
| Placement rationale | VM **Why here?** | `GET .../placement-rationale` |
| Project aggregate compliance | Blue membership on project tab / explorer | Intersection of all child VMs + networks |
| Network delete guard | **Projects** → Networks | HTTP **409** when blocked |
| IP pool delete | **IPAM** → Delete pool | HTTP **409** when blocked |

## Phase 7+ GRC extensions

GRC-style primitives (console **Compliance → GRC**):

| Capability | Notes |
|------------|--------|
| Standards & controls | CRUD under org |
| Cycles | Per standard; **Status** shows evidence coverage + expiring/expired checks |
| Evidence | Multipart upload; design / implementation / operating; object store; supersede; delete |
| Packs | Validate + apply JSON → standards/controls ([packs.md](../compliance/packs.md)) |
| PDF export | Request from GRC; browser polls and downloads once |
| Qualitative characteristics | MoSCoW, description, kind; migrate legacy traits |

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

**Catalog items** (placement standards) are linked on:

1. **Provider** — applies to all agents on that provider.
2. **Region** — applies to agents in that region **or any sub-region** (parent chain via registry `parent_region_id`).

**Qualitative characteristics** use the same provider/region link model but are defined in the GRC catalog first, then attached under **Infrastructure** (checkbox panel). Both catalog slugs and characteristic slugs appear in Explorer trait filters.

Legacy `provider_traits` / `region_traits` **writes return HTTP 410**. Use GRC **Migrate legacy traits** or `POST .../qualitative-characteristics/migrate-from-legacy-traits` before decommissioning old integrations.

Configure catalog standards: **Infrastructure** → expand provider or region → **Region compliance standards** / **Provider compliance** → Save.

Roles: `admin` and `compliance_admin` can edit infrastructure profiles; `compliance_engineer` assigns per-resource criticality.

## Evidence storage (object store)

Evidence and export PDF bytes live outside PostgreSQL.

| Mode | Configuration |
|------|----------------|
| **local** (dev) | `OBJECT_STORE_KIND=local`, files under `OBJECT_STORE_LOCAL_DIR` (default `./data/object-store`) |
| **s3** (MinIO/SeaweedFS) | `OBJECT_STORE_KIND=s3`, `OBJECT_STORE_BUCKET`, optional endpoint/region/credentials, `OBJECT_STORE_PREFIX` |

Compose dev stack includes SeaweedFS S3 when using the default compliance service env.

## Operator workflows

### Placement compliance

1. **Catalog** — define org standards (name, slug, MoSCoW).
2. **Infrastructure** — attach catalog items and/or qualitative characteristics to provider/region.
3. **Projects** — optional direct project standards (green); blue when all children align.
4. **VMs / networks** — per-resource assignment or grey inheritance.
5. **Explorer** — gaps (missing catalog slug, missing placement trait); KPI cards on Overview.
6. **Checks** — owners and validity; cycle status surfaces expiring/expired counts.

### GRC audit workflow

1. **GRC** — create or import standards/controls (pack apply).
2. **Cycles** — open a cycle on a standard; use **Status** for evidence-by-category gaps.
3. **Evidence** — upload per control (optionally tied to cycle); replace/supersede as needed.
4. **Export PDF** — from standard detail; includes generated time and requester in the document.

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

## Known gaps (backlog)

| Item | Notes |
|------|--------|
| **Placement `config_drift`** | Field on placement rationale; not populated from inventory yet |
| **Check alerter** | Periodic scan → structlog only; no email/ES notification |
| **Kibana compliance dashboards** | Spike only — [kibana/README.md](../compliance/kibana/README.md) |
| **GRC Overview charts** | No pie chart of control/evidence posture (FRAMEWORK_PLAN); KPI cards only |
| **Explorer ↔ GRC** | No explorer filters for missing evidence per cycle/standard |
| **Bundled framework packs** | JSON format documented; ISO/BIO/DigiD artifacts shipped separately |

## Related docs

- [ADR 0010](../architecture/adrs/0010-know-why-and-asset-criticality.md)
- [Compliance concepts](../compliance/README.md)
- [Compliance packs](../compliance/packs.md)
- [services/compliance/README.md](../../services/compliance/README.md)
- [services/projects/README.md](../../services/projects/README.md) — delete guards
- [phase6-release-and-validation.md](phase6-release-and-validation.md) — topology and breakout
