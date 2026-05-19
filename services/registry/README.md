# huy-registry

Agent and hypervisor registry (Phase 1).

## Scope

- **`platform_admin`:** CRUD providers, regions, agents; assign organization; export/rotate agent token (one-time export); test connection
- **Org `admin`:** read agents for their organization only
- **Inventory service:** internal poll-targets API (service token)

## Run locally

```bash
cd services/registry
cp .env.example .env
make install
make run
```

With Docker Compose from repo root: `docker compose up -d --build` (port **8082**).

## API (JWT from IAM)

| Method | Path | Role |
|--------|------|------|
| POST | `/api/v1/providers` | platform_admin |
| GET | `/api/v1/providers` | platform_admin |
| POST | `/api/v1/providers/{id}/regions` | platform_admin |
| GET | `/api/v1/providers/{id}/regions` | platform_admin |
| POST | `/api/v1/agents` | platform_admin (returns `agent_token` once) |
| GET | `/api/v1/agents` | inventory:read (org-filtered) |
| GET | `/api/v1/agents/{id}` | inventory:read |
| PATCH | `/api/v1/agents/{id}` | platform_admin |
| POST | `/api/v1/agents/{id}/export-token` | platform_admin (once) |
| POST | `/api/v1/agents/{id}/rotate-token` | platform_admin |
| POST | `/api/v1/agents/{id}/test-connection` | platform_admin |

Internal (header `X-Huy-Service-Token`):

| Method | Path |
|--------|------|
| GET | `/api/v1/internal/poll-targets` |
| PATCH | `/api/v1/internal/agents/{id}/poll-status` |

## Configuration

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL or SQLite |
| `JWT_SECRET` / `JWT_ISSUER` | Same as IAM |
| `AGENT_TOKEN_ENCRYPTION_KEY` | Fernet key material for poller (hash stored per ADR 0005) |
| `INVENTORY_SERVICE_TOKEN` | Shared secret with inventory service |

See [ADR 0005](../../docs/architecture/adrs/0005-agent-token-vault.md).
