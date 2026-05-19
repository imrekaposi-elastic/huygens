# Integration tests (placeholder)

Cross-service tests for Phases 0–3+ will live here. They are **not** run by `make test`.

## Planned scope

1. Bootstrap IAM (local login) → obtain JWT
2. Register agent in registry (platform admin)
3. Create project → list agents → proxy GET `/vms` against mock or test agent
4. Inventory poller marks agent connected (optional)

## Running (future)

```bash
docker compose up -d --build
export HUY_E2E=1
pytest -m integration tests/integration
```

Until implemented, this directory documents the contract only.
