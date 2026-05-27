# Compliance service (`huy-compliance`)

Phase 7 control-plane service: org compliance catalog, infrastructure placement standards, asset criticality, compliance checks, explorer, and placement explainability.

Port **8086** (`HUY_COMPLIANCE_PORT`). Console and nginx proxy org APIs to this service.

## Run locally

```bash
cd services/compliance
uv sync
uv run huy-compliance
```

With Docker Compose from repo root: `docker compose up -d --build compliance`.

## API (summary)

Base: `/api/v1/organizations/{organization_id}` (JWT from IAM).

| Area | Methods | Notes |
|------|---------|--------|
| Catalog | `GET/POST/PATCH/DELETE .../compliance-catalog` | Org standards (slug, MoSCoW) |
| Checks | `GET/POST/PATCH/DELETE .../compliance-checks` | Owner, validity, status |
| Dashboard | `GET .../compliance-dashboard` | KPI counts |
| Explorer | `GET .../compliance-explorer`, `.../facets`, `.../suggest` | Filters; pagination |
| Placement rationale | `GET .../resources/{type}/placement-rationale` | Query: `project_id`, `agent_id`, `name` |
| VM/network criticality | `GET/PUT .../projects/{pid}/resources/{type}/{name}/criticality` | Query: `agent_id` |
| Project criticality | `GET/PUT .../projects/{pid}/criticality` | Includes `aggregate_compliance_items` |
| Provider compliance | `GET/PUT .../infrastructure-providers/{id}/compliance-profile` | Catalog item checkboxes |
| Region compliance | `GET/PUT .../regions/{id}/compliance-items` | Per region node |
| Traits (legacy) | `GET/POST .../traits`, region/provider trait routes | Free-form keys; **not used by console inheritance** |

### Membership model

- **Direct** — `compliance_items` on `AssetCriticalityOut` / `direct_catalog_items` on explorer rows.
- **Inherited (placement)** — provider + region catalog links; region **ancestor chain** via registry internal regions API.
- **Aggregate (project)** — intersection of effective compliance across all project VMs and networks; `aggregate_compliance_items` / `aggregate_catalog_items`.

Effective compliance for a VM/network = merge(direct, placement inherited).

### RBAC (org-scoped)

| Role | Typical access |
|------|----------------|
| `compliance_reader` | Read catalog, explorer, criticality |
| `compliance_engineer` | Assign resource criticality |
| `compliance_admin` | Infrastructure compliance + checks |
| `admin` | Full org compliance |

Requires `inventory:read` for registry agent lookups (explorer, rationale, inheritance).

## Dependencies

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL (compose) or SQLite (dev) |
| `JWT_SECRET` / `JWT_ISSUER` | Same as IAM |
| `REGISTRY_URL` | Agent + internal regions list |
| `PROJECTS_URL` | Resource assignments, project names |
| `PROJECTS_SERVICE_TOKEN` | Internal projects API; also accepted by registry internal routes |
| `CHECK_ALERT_ENABLED` | Background check expiry scan (default `true`) |

Registry internal (service token): `GET /api/v1/internal/infrastructure-providers/{id}/regions` — flat regions with `parent_region_id` for lineage inheritance.

## Tests

```bash
make test
```

Notable: `test_explorer.py`, `test_project_aggregate.py`, `test_region_tree.py`, `test_phase7.py`.

Operational guide: [docs/operations/phase7-compliance-and-lifecycle-guards.md](../../docs/operations/phase7-compliance-and-lifecycle-guards.md).
