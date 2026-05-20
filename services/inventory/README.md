# huy-inventory

Inventory poller and dashboard API (Phase 1).

## Scope

- Background poller: registry poll-targets → agent `/api/v1/agent`, `/vms`, `/networks`
- PostgreSQL snapshots; `config_drift` when VM/network set changes vs previous poll
- Dashboard API for org admins (`inventory:read`)
- Kafka publish: `huy.inventory.snapshots` via shared `huy-events` (see `KAFKA_BOOTSTRAP`, `KAFKA_PUBLISH_ENABLED`)

## Run locally

```bash
cd services/inventory
cp .env.example .env
make install
make run
```

Docker Compose: port **8083**, depends on registry.

## API (JWT from IAM)

| Method | Path | Role |
|--------|------|------|
| GET | `/api/v1/inventory/agents` | inventory:read |
| GET | `/api/v1/inventory/agents/{id}` | inventory:read |
| GET | `/api/v1/inventory/organizations/{org_id}/dashboard` | inventory:read |
| GET | `/api/v1/inventory/events/stream` | inventory:read (SSE; **Bearer header only**, not `?token=`) |

## Configuration

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL or SQLite |
| `REGISTRY_URL` | Registry base URL |
| `JWT_SECRET` / `JWT_ISSUER` | Same as IAM |
| `INVENTORY_SERVICE_TOKEN` | Same as registry |
| `POLL_INTERVAL_SECONDS` | Default **30** (min **10**) |
| `INVENTORY_POLLER_ENABLED` | Set `false` in tests |
| `KAFKA_BOOTSTRAP` | Comma-separated brokers (default `kafka:9092` in Compose) |
| `KAFKA_PUBLISH_ENABLED` | Set `false` in unit tests without a broker |
| `KAFKA_CLIENT_ID` | Optional Kafka client id |
| `KAFKA_SSE_CONSUMER_ENABLED` | Broadcast consumer for SSE hub (default `true` in Compose) |

SSE clients must use fetch-based streaming with `Authorization: Bearer` — see [ADR 0011](../../docs/architecture/adrs/0011-sse-auth-via-authorization-header.md).

Schema: [inventory-snapshot.schema.json](../../schemas/kafka/inventory-snapshot.schema.json)
