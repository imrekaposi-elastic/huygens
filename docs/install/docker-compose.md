# Docker Compose — local mock stack

Run the control plane and PostgreSQL with one command. The libvirt agent stays on the hypervisor host (needs KVM); use Compose for IAM, registry, and inventory.

## Prerequisites

- Docker Engine 24+ with Compose v2
- Ports free: `5432`, `8081`–`8086`, `9092`, `5173` (PostgreSQL, control plane, Kafka, console)

## Start

```bash
cp compose.env.example .env
docker compose up -d --build
```

Wait until healthy:

```bash
docker compose ps
```

## Endpoints

| Service | URL | Notes |
|---------|-----|--------|
| IAM | http://localhost:8081/docs | Login, orgs, RBAC |
| Registry | http://localhost:8082/docs | Scaffold (Phase 1) |
| Inventory | http://localhost:8083/docs | Poller + SSE |
| Projects | http://localhost:8084/docs | Project CRUD, IPAM, links, agent proxy |
| Breakout controller | http://localhost:8085/health | WireGuard link planning (internal) |
| Compliance | http://localhost:8086/docs | Phase 7 catalog, explorer, criticality |
| **Console** | http://localhost:5173 | Web UI (nginx proxies IAM, projects, inventory, registry, **compliance**) |
| PostgreSQL | `localhost:5432` | user/db/password: `huy` |

### Bootstrap login (IAM)

Default from `compose.env.example`:

```bash
curl -s -X POST http://localhost:8081/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"platform-admin","password":"platform-admin-dev"}' | jq .
```

## Kafka

Kafka starts with the default stack (`KAFKA_BOOTSTRAP=kafka:9092`). Override in `.env` for external or clustered brokers (comma-separated list).

First boot may take ~30–60s while the broker passes its healthcheck. A one-shot **`kafka-init`** service then creates application topics (`huy.agent.events`, `huy.inventory.snapshots`, `huy.audit.events`, `huy.network.links`) before control-plane producers start. See [ADR 0004](../architecture/adrs/0004-kafka-event-bus.md) and [`docker/kafka/init-topics.sh`](../../docker/kafka/init-topics.sh).

Verify topics after `docker compose up`:

```bash
docker compose exec kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --list | grep '^huy\.'
```

For **external** Kafka (not the Compose broker), run `init-topics.sh` with `KAFKA_BOOTSTRAP` pointing at your cluster.

## Stop

```bash
docker compose down
# remove DB volume:
docker compose down -v
```

## Libvirt agent

Not included in Compose (requires host libvirt/KVM). Topology links and breakout apply run on the hypervisor agent — **upgrade agents whenever you upgrade `projects` / `breakout-controller`**.

On dommel or your laptop:

```bash
cd agents/libvirt && make run
```

Production hypervisors: [agents/libvirt/README.md](../../agents/libvirt/README.md#upgrading-the-agent-phase-6) and [Phase 6 operations](../operations/phase6-release-and-validation.md).

Point the agent at registry when Phase 1 enrollment exists.
