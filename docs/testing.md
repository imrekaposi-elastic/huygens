# Testing strategy

## Continuous integration (default)

GitHub Actions workflow [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) runs on every push to `main` and on pull requests:

| Job | Command | Notes |
|-----|---------|--------|
| **unit** | `make test` | Python services + console (`npm test`); no Docker |
| **integration** | `docker compose up -d --build` → `scripts/wait-for-stack.sh` → `make test-integration` | Full Compose stack on `ubuntu-latest` |

Reproduce CI locally:

```bash
make test
cp compose.env.example .env && docker compose up -d --build
bash scripts/wait-for-stack.sh
make test-integration
# or: make test-ci   # unit then integration (stack must already be up for the second step)
```

## Unit tests

Run all control-plane unit tests from the repo root:

```bash
make test
```

Requires **Python 3.11+** with `python3` on `PATH`. The Makefile creates a repo-local `.venv` automatically (PEP 668–safe on macOS/Homebrew).

This executes pytest in each service:

| Package | Directory |
|---------|-----------|
| huy-events | `shared/huy_events` |
| IAM | `services/iam` |
| Registry | `services/registry` |
| Inventory | `services/inventory` |
| Projects | `services/projects` |
| Compliance | `services/compliance` |
| Breakout controller | `services/breakout-controller` (`go test ./...`) |
| Console | `web` (`npm test`) |

Shared packages `huy_auth` and `huy_events` are installed once via `make test-deps` before services that depend on them.

Each service uses in-memory SQLite, mocked HTTP (respx where needed), and synthetic JWTs signed with a test secret.

Agent unit tests: `make -C agents/libvirt test`.

## Integration tests (compose stack)

Cross-service tests live under `tests/integration/`. They are **not** part of `make test` alone; they **are** part of default CI and `make test-ci`.

```bash
docker compose up -d --build
bash scripts/wait-for-stack.sh   # optional locally; CI runs this automatically
make test-integration
```

See [tests/integration/README.md](../tests/integration/README.md) for environment variables and module layout.

**Phase 6 scope:** `test_network_links.py` covers link API and validation; `test_link_reconcile.py` exercises **create → reconcile → `connected`** for local and WireGuard links with mocked agent/breakout-controller HTTP. Cross-host **data-plane** traffic still requires [manual runbooks](../tests/integration/README.md#manual-two-agent-wireguard-link-test-phase-6).

**Phase 7 / guards:** `services/compliance/tests/` (explorer, project aggregate, region lineage); `services/projects/tests/test_network_delete_guard.py`, `test_ipam.py` (pool delete).

Conventions:

- Mark tests with `@pytest.mark.integration`
- Require `HUY_E2E=1` (set automatically by `make test-integration`)
- Use ephemeral organizations where possible; tests clean up org + projects after mutation
- `@pytest.mark.requires_agent` skips when no connected libvirt agent exists

### PostgreSQL schema upgrades

Projects unit tests use **SQLite**; production Compose uses **PostgreSQL**. Column additions (e.g. `ip_pools.pool_kind`) are applied via `apply_schema_upgrades` on projects startup. After pulling schema changes, restart `projects` against existing volumes — or use `docker compose down -v` for a clean dev DB.

## Adding tests for a new phase

1. Add service unit tests under `services/<name>/tests/`.
2. Extend the root `Makefile` `test-unit` target if a new package is added.
3. When the phase needs multiple running services, extend `tests/integration/` and document any new env vars in `tests/integration/README.md`.
