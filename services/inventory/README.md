# huy-inventory

Inventory poller and desired vs actual state (Phase 1).

## Scope

- Poll registered agents (default 30s, minimum 10s)
- Persist snapshots to PostgreSQL
- Publish `huy.inventory.snapshots` to Kafka when configured
- Surface config drift vs desired state

## Run (scaffold)

```bash
cd services/inventory
pip install -e .
huy-inventory
```

Default: `http://127.0.0.1:8083`

## Configuration

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL |
| `REGISTRY_URL` | Registry service base URL |
| `POLL_INTERVAL_SECONDS` | Default 30 |
| `KAFKA_BOOTSTRAP` | Optional |

Schema: [schemas/kafka/inventory-snapshot.schema.json](../../schemas/kafka/inventory-snapshot.schema.json)
