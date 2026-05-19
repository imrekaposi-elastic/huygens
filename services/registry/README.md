# huy-registry

Agent and hypervisor registry (Phase 1).

## Scope

- Register agents (`platform_admin` only)
- Token vault (hash storage, one-time export)
- Provider, region, organization assignment
- Agent connection health

## Run (scaffold)

```bash
cd services/registry
pip install -e .
huy-registry
```

Default: `http://127.0.0.1:8082`

## Configuration

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL |
| `KAFKA_BOOTSTRAP` | Optional; `huy.agent.events` |

Contract with agents: OpenAPI in [agents/libvirt](../../agents/libvirt/).
