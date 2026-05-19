# Huygens Projects (`huy-projects`)

Phase 3–4 control-plane service: **project CRUD**, **IPAM**, **desired-state records**, and an **authenticated proxy** to libvirt agents.

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
| `*` | `/api/v1/projects/{id}/agents/{agent_id}/networks` | Proxy; enforces readonly delete; **IPAM** on create |
| POST | `/api/v1/organizations/{org_id}/ipam/pools` | RFC1918 pool (org admin) |
| POST | `/api/v1/organizations/{org_id}/ipam/wizard/plan` | Subnet wizard plan |
| POST | `/api/v1/organizations/{org_id}/ipam/projects/{id}/wizard/apply` | Reserve planned subnets |

### Network create with IPAM

```json
POST /api/v1/projects/{project_id}/agents/{agent_id}/networks
{
  "name": "lab0",
  "ipam": { "pool_id": "<pool-uuid>", "hosts": 50 }
}
```

Or use a pre-reserved `allocation_id` from the wizard.

## Configuration

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL (compose) or SQLite (dev) |
| `JWT_SECRET` / `JWT_ISSUER` | Same as IAM |
| `REGISTRY_URL` | Registry base URL |
| `PROJECTS_SERVICE_TOKEN` | Must match registry `PROJECTS_SERVICE_TOKEN` |
| `IPAM_ENFORCE` | Reject manual `ipv4_cidr` on network create (default `true`) |

## Tests

```bash
make test
```

Unit tests mock registry and agent HTTP with **respx**. Cross-service integration tests are planned under `tests/integration/` (see repo `docs/testing.md`).
