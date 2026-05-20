# Huygens

Open-source infrastructure operations platform: **know where** workloads run and **why**
they are placed there. Apache License 2.0.

## Quick start

**Control plane and console** run in Docker Compose. The **libvirt agent** runs on each
KVM hypervisor (host libvirt/KVM required) and is not containerized in the default stack.

```bash
cp compose.env.example .env
docker compose up -d --build
```

Open the console at **http://localhost:5173** and sign in with the bootstrap user from
`.env` (default `platform-admin` / `platform-admin-dev`). First-time platform admins with
no organizations are guided through **Setup** in the UI.

| Service | Port | Role |
|---------|------|------|
| Console (nginx) | 5173 | Web UI |
| IAM | 8081 | Auth, orgs, users, RBAC |
| Registry | 8082 | Agents, infrastructure, regions |
| Inventory | 8083 | Poll agents, dashboard, live events |
| Projects | 8084 | Projects, IPAM, agent API proxy |
| PostgreSQL | 5432 | System of record |
| Kafka | 9092 | Inventory change events |

Check health: `docker compose ps`. Details: [docs/install/docker-compose.md](docs/install/docker-compose.md).

Optional Keycloak SSO:

```bash
docker compose --profile sso up -d --build
```

## Libvirt agent (hypervisor)

Install and run on the host that manages VMs (not via Compose):

```bash
cd agents/libvirt
cp .env.example .env
make install
make run
```

Register the agent in the console (**Agents**), assign it to a region, then use **IPAM** and
**Projects** for networks and workloads. See [agents/libvirt/README.md](agents/libvirt/README.md).

## Repository layout

| Path | Description |
|------|-------------|
| [agents/libvirt](agents/libvirt/) | KVM hypervisor agent (REST API, libvirt, networking) |
| [services/iam](services/iam/) | Authentication, organizations, RBAC |
| [services/registry](services/registry/) | Agent registry, infrastructure providers, regions |
| [services/inventory](services/inventory/) | Agent polling, inventory API, SSE |
| [services/projects](services/projects/) | Projects, IPAM, proxied operator APIs |
| [web](web/) | Console SPA (built into the `web` Compose service) |
| [shared/huy_events](shared/huy_events/) | Shared Kafka / CloudEvents client |
| [schemas/kafka](schemas/kafka/) | CloudEvents JSON schemas |
| [docs/architecture](docs/architecture/) | ADRs, ERD, diagrams |
| [docs/install/air-gapped.md](docs/install/air-gapped.md) | Offline installation |
| [docs/PHASED_PLAN.md](docs/PHASED_PLAN.md) | Delivery roadmap |
| [FRAMEWORK_PLAN.md](FRAMEWORK_PLAN.md) | Product scope and NFRs |

## Development

**Console (hot reload, proxies to local services):**

```bash
cd web && npm install && npm run dev
```

Run individual services on the host instead of Compose when debugging — see each
service README under `services/`.

**Agent tests:**

```bash
make -C agents/libvirt test
```

## Contributing

[CONTRIBUTING.md](CONTRIBUTING.md) · [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) · [LICENSE](LICENSE)
