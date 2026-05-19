# Huygens Projects (`huy-projects`)

Phase 3 control-plane service: **project CRUD**, **desired-state records**, and an **authenticated proxy** to libvirt agents.

Operators call this service instead of hitting agent Swagger directly. The proxy:

- Validates IAM JWT and project/org RBAC
- Resolves agent URL + token via registry internal API (`X-Huy-Service-Token`)
- Rejects DELETE on readonly networks (`default` or `readonly: true`)

## Run locally

```bash
cd services/projects
cp .env.example .env
make install
make run
```

Default port: **8084**.

## API (summary)

| Method | Path | Notes |
|--------|------|--------|
| GET | `/health` | Liveness |
| POST | `/api/v1/projects` | Org admin or platform admin |
| GET | `/api/v1/projects` | Filter by org; RBAC-scoped list |
| GET | `/api/v1/projects/{id}/agents` | Agents in project's org (via registry) |
| `*` | `/api/v1/projects/{id}/agents/{agent_id}/vms` | Proxy to agent |
| `*` | `/api/v1/projects/{id}/agents/{agent_id}/networks` | Proxy; enforces readonly delete |

## Configuration

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL (compose) or SQLite (dev) |
| `JWT_SECRET` / `JWT_ISSUER` | Same as IAM |
| `REGISTRY_URL` | Registry base URL |
| `PROJECTS_SERVICE_TOKEN` | Must match registry `PROJECTS_SERVICE_TOKEN` |

## Tests

```bash
make test
```

Unit tests mock registry and agent HTTP with **respx**. Cross-service integration tests are planned under `tests/integration/` (see repo `docs/testing.md`).
