# Docker Compose — local mock stack

Run the control plane and PostgreSQL with one command. The libvirt agent stays on the hypervisor host (needs KVM); use Compose for IAM, registry, and inventory.

## Prerequisites

- Docker Engine 24+ with Compose v2
- Ports free: `5432`, `8081`–`8083` (and `9092` if using Kafka profile)

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
| Inventory | http://localhost:8083/docs | Scaffold (Phase 1) |
| PostgreSQL | `localhost:5432` | user/db/password: `huy` |

### Bootstrap login (IAM)

Default from `compose.env.example`:

```bash
curl -s -X POST http://localhost:8081/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"platform-admin","password":"platform-admin-dev"}' | jq .
```

## Optional: Kafka

```bash
docker compose --profile kafka up -d --build
```

Sets `KAFKA_BOOTSTRAP=kafka:9092` for registry/inventory env (used in Phase 1+).

## Stop

```bash
docker compose down
# remove DB volume:
docker compose down -v
```

## Libvirt agent

Not included in Compose (requires host libvirt/KVM). On dommel or your laptop:

```bash
cd agents/libvirt && make run
```

Point the agent at registry when Phase 1 enrollment exists.
