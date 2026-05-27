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
| Projects | 8084 | Projects, IPAM, network links, agent API proxy |
| Breakout controller | 8085 | WireGuard link planning (internal) |
| Compliance | 8086 | Org catalog, explorer, asset criticality, placement rationale |
| PostgreSQL | 5432 | System of record |
| Kafka | 9092 | Inventory snapshots, link events (`huy.network.links`) |

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

Register the agent in the console (**Agents**), assign it to a region, then use **IPAM**,
**Projects**, and **Topology** for networks, workloads, and links. After upgrading Compose,
[upgrade the agent on each hypervisor](agents/libvirt/README.md#upgrading-the-agent-phase-6).
See [docs/operations/phase6-release-and-validation.md](docs/operations/phase6-release-and-validation.md) and [docs/operations/phase7-compliance-and-lifecycle-guards.md](docs/operations/phase7-compliance-and-lifecycle-guards.md).

## Repository layout

| Path | Description |
|------|-------------|
| [agents/libvirt](agents/libvirt/) | KVM hypervisor agent (REST API, libvirt, networking) |
| [services/iam](services/iam/) | Authentication, organizations, RBAC |
| [services/registry](services/registry/) | Agent registry, infrastructure providers, regions |
| [services/inventory](services/inventory/) | Agent polling, inventory API, SSE |
| [services/projects](services/projects/) | Projects, IPAM, network links, proxied operator APIs |
| [services/breakout-controller](services/breakout-controller/) | WireGuard link planning (internal) |
| [services/compliance](services/compliance/) | Compliance catalog, explorer, criticality, explainability |
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

**Tests:** `make test` (unit). **CI** also runs integration tests against Compose; locally:

```bash
docker compose up -d --build
bash scripts/wait-for-stack.sh
make test-integration
```

See [docs/testing.md](docs/testing.md).

## Contributing

[CONTRIBUTING.md](CONTRIBUTING.md) · [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) · [LICENSE](LICENSE)
