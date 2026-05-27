# Huygens Projects (`huy-projects`)

Phase 3–6 control-plane service: **project CRUD**, **IPAM**, **network links**, **desired-state records**, and an **authenticated proxy** to libvirt agents.

Operators call this service instead of hitting agent Swagger directly. The proxy:

- Validates IAM JWT and project/org RBAC
- Resolves agent URL + token via registry internal API (`X-Huy-Service-Token`)
- Rejects DELETE on readonly networks (`default` or `readonly: true`) — **403**
- Rejects DELETE when VMs, topology links, or active breakout still use the network — **409** (see below)

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
| `*` | `/api/v1/projects/{id}/agents/{agent_id}/networks` | Proxy; **409** delete guards; **IPAM** on create; default `purge=true` on delete |
| DELETE | `/api/v1/organizations/{org_id}/ipam/pools/{pool_id}` | **409** if allocations or overlay links in use |
| GET/POST/DELETE | `/api/v1/organizations/{org_id}/network-links` | Phase 6 link CRUD |
| GET | `/api/v1/organizations/{org_id}/topology` | Phase 6 vnet graph + links |
| POST | `/api/v1/organizations/{org_id}/ipam/pools` | RFC1918 or `pool_kind: overlay` |
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

### Phase 6 network links

- **Cross-hypervisor:** `link_type: wireguard`, requires `overlay_pool_id` and two agents.
- **Same hypervisor:** `link_type: local`, no overlay pool; requires both vnets to have CIDRs.

Reconciler runs when `LINK_RECONCILE_ENABLED=true` (default). Publishes to Kafka topic `huy.network.links` when `KAFKA_PUBLISH_ENABLED=true` (topic created by Compose `kafka-init`; see [docker-compose.md](../../docs/install/docker-compose.md)).

### Network delete guards (409)

Before deleting a vnet, the proxy checks (in order):

1. No VMs on the agent still attached to this network name
2. No active topology links (`NetworkLink`, status ≠ `deleting`) on this endpoint
3. No active breakout (WireGuard or flat `enabled` on agent)

Remove blockers first; links are **not** auto-deleted. Implementation: `network_delete_guard.py`.

### IP pool delete (409)

`DELETE .../ipam/pools/{pool_id}` fails while:

- Any **reserved** or **allocated** subnet exists in a vnet pool
- Any topology link references an **overlay** pool

Operational guides: [phase6](../../docs/operations/phase6-release-and-validation.md), [phase7](../../docs/operations/phase7-compliance-and-lifecycle-guards.md).

## Configuration

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL (compose) or SQLite (dev) |
| `JWT_SECRET` / `JWT_ISSUER` | Same as IAM |
| `REGISTRY_URL` | Registry base URL |
| `PROJECTS_SERVICE_TOKEN` | Must match registry `PROJECTS_SERVICE_TOKEN` |
| `BREAKOUT_CONTROLLER_URL` | Internal breakout-controller (default `http://breakout-controller:8085`) |
| `BREAKOUT_SERVICE_TOKEN` | Service token for plan/revoke |
| `IPAM_ENFORCE` | Reject manual `ipv4_cidr` on network create (default `true`) |
| `LINK_RECONCILE_ENABLED` | Background link reconciler (default `true`) |
| `KAFKA_PUBLISH_ENABLED` | Publish link events (default `true`) |

## Tests

```bash
make test
```

Unit tests mock registry and agent HTTP with **respx**. Cross-service integration smoke:
`make test-integration` from repo root — see [tests/integration/README.md](../../tests/integration/README.md).
