# Huygens console

React SPA for operators. Phase 5 (projects, inventory, IPAM) and Phase 6 (**Topology** — network linking) are in the console; see [PHASED_PLAN.md](../docs/PHASED_PLAN.md).

## Development

```bash
# Control plane must be running (docker compose up)
cd web
npm install
npm run dev
```

Open http://localhost:5173 — Vite proxies `/api/v1/*` to IAM (8081), registry (8082), inventory (8083), projects (8084).

Default login (from `compose.env.example`): `platform-admin` / `platform-admin-dev`

**First login:** platform admins with no organizations are sent to `/setup` — a multi-step wizard to create an organization, optional first project, and review security notes (no default org is seeded).

**Platform admin nav:** **Fabric** (libvirt-agent, …) → **Infrastructure** (vendor + region tree) → **Agents** (enroll at a region) → Dashboard / Projects / **Topology** / IPAM.

**Topology (Phase 6):** connect vnets on the graph (drag or click source then target). Cross-hypervisor links need an overlay IPAM pool; same-hypervisor links use direct routing (`local`). Link detail shows `last_error` when reconcile fails — often outdated libvirt agent; see [Phase 6 operations](../docs/operations/phase6-release-and-validation.md).

**DB reset:** This release changes registry/projects schema (`infrastructure_providers`, hierarchical regions, `agent_technologies`). Run `docker compose down -v` before upgrading.

## Production build

```bash
npm run build
# or via Compose:
docker compose up -d web   # http://localhost:5173 — nginx + API proxy
```

## Auth

- **Local:** `POST /api/v1/auth/login` via login form
- **OIDC:** IAM callback with `redirect=true` → `#access_token=` on `/auth/callback` (never query string). See [ADR 0011](../docs/architecture/adrs/0011-sse-auth-via-authorization-header.md).

## Live inventory

Uses `@microsoft/fetch-event-source` with `Authorization: Bearer` — **not** `EventSource`.

## Tests

```bash
npm test
```
