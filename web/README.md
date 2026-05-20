# Huygens console

Phase 5 web UI — React SPA for operators.

## Development

```bash
# Control plane must be running (docker compose up)
cd web
npm install
npm run dev
```

Open http://localhost:5173 — Vite proxies `/api/v1/*` to IAM (8081), registry (8082), inventory (8083), projects (8084).

Default login (from `compose.env.example`): `platform-admin` / `platform-admin-dev`

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
