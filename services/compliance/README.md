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
| GRC standards | `GET/POST/PATCH/DELETE .../compliance-standards` | Top-level standards (ISO/BIO/etc.) |
| Controls | `GET/POST .../compliance-standards/{sid}/controls` + `PATCH/DELETE .../compliance-controls/{id}` | Controls under a standard |
| Cycles | `GET/POST .../compliance-standards/{sid}/cycles` + `PATCH/DELETE .../compliance-cycles/{id}` | Repeated assessment cycles |
| Evidence | `GET/POST .../compliance-controls/{cid}/evidence` + `GET .../compliance-evidence/{id}/download` | Upload/list/download evidence |
| Packs | `GET .../compliance-packs` + `POST .../compliance-packs/validate` + `POST .../import` | Dry-run and apply JSON packs |
| Exports | `POST .../compliance-export` + `GET .../compliance-export/{job_id}` + `GET .../download` | PDF export (poll status, one-time download) |
| Qualitative characteristics | `GET/POST/PATCH/DELETE .../qualitative-characteristics` + provider/region link endpoints + `POST .../migrate-from-legacy-traits` | Placement traits for Explorer/inheritance |
| Dashboard | `GET .../compliance-dashboard` | KPI counts |
| Explorer | `GET .../compliance-explorer`, `.../facets`, `.../suggest` | Filters; pagination |
| Placement rationale | `GET .../resources/{type}/placement-rationale` | Query: `project_id`, `agent_id`, `name` |
| VM/network criticality | `GET/PUT .../projects/{pid}/resources/{type}/{name}/criticality` | Query: `agent_id` |
| Project criticality | `GET/PUT .../projects/{pid}/criticality` | Includes `aggregate_compliance_items` |
| Provider compliance | `GET/PUT .../infrastructure-providers/{id}/compliance-profile` | Catalog item checkboxes |
| Region compliance | `GET/PUT .../regions/{id}/compliance-items` | Per region node |
| Traits (legacy) | `GET .../traits` (deprecated), writes **410** | Use qualitative characteristics + `/migrate-from-legacy-traits` |

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
| `OBJECT_STORE_KIND` | `local` (dev) or `s3` (S3-compatible / MinIO) |
| `OBJECT_STORE_LOCAL_DIR` | Base directory for `local` storage (default `./data/object-store`) |
| `OBJECT_STORE_BUCKET` | Bucket name for `s3` mode |
| `OBJECT_STORE_ENDPOINT` | Optional S3 endpoint URL (e.g. MinIO) |
| `OBJECT_STORE_REGION` | Optional AWS region |
| `OBJECT_STORE_ACCESS_KEY_ID` / `OBJECT_STORE_SECRET_ACCESS_KEY` | Optional static credentials |
| `OBJECT_STORE_PREFIX` | Key prefix for evidence/exports |

Registry internal (service token): `GET /api/v1/internal/infrastructure-providers/{id}/regions` — flat regions with `parent_region_id` for lineage inheritance.

## Tests

```bash
make test
```

Notable: `test_explorer.py`, `test_project_aggregate.py`, `test_region_tree.py`, `test_phase7.py`.

Operational guide: [docs/operations/phase7-compliance-and-lifecycle-guards.md](../../docs/operations/phase7-compliance-and-lifecycle-guards.md).
