# Testing strategy

## Continuous integration (default)

GitHub Actions workflow [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) runs on every push to `main` and on pull requests. Each microservice has its own job (matrix), so failures are scoped to a single package.

| Job | Command | Notes |
|-----|---------|--------|
| **unit** (`Unit (test-*)`) | `make test-<target>` | One job per shared lib, Python service, Go service, and console |
| **integration** | `make test-integration-<service>` | One Compose stack per workflow run; separate CI steps per service (`stack`, `iam`, `registry`, `inventory`, `projects`, `web`) |

Optional: set repository secrets `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN` for authenticated pulls (`apache/kafka`, `chrislusf/seaweedfs` still use Docker Hub).

Reproduce CI locally:

```bash
make test-iam                    # single unit target
make test                        # all unit targets
cp compose.env.example .env && docker compose up -d --build
bash scripts/wait-for-stack.sh
make test-integration-projects   # single integration target
make test-integration            # all integration targets
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
| huy-telemetry | `shared/huy_telemetry` |
| IAM | `services/iam` |
| Registry | `services/registry` |
| Inventory | `services/inventory` |
| Projects | `services/projects` |
| Compliance | `services/compliance` |
| Breakout controller | `services/breakout-controller` (`go test ./...`) |
| SSH gateway | `services/ssh-gateway` (`go test ./...`) |
| Console | `web` (`npm test`) |

Shared packages `huy_auth`, `huy_events`, and `huy_telemetry` are installed once via `make test-deps` before services that depend on them (`[tool.uv.sources]` path deps are not resolved by plain `pip` alone).

Each service uses in-memory SQLite, mocked HTTP (respx where needed), and synthetic JWTs signed with a test secret.

Agent unit tests: `make -C agents/libvirt test`.

## Integration tests (compose stack)

Cross-service tests live under `tests/integration/<service>/`. They are **not** part of `make test` alone; they **are** part of default CI and `make test-ci`.

```bash
docker compose up -d --build
bash scripts/wait-for-stack.sh   # optional locally; CI runs this automatically
make test-integration-iam      # or test-integration-projects, etc.
make test-integration          # all service directories
```

See [tests/integration/README.md](../tests/integration/README.md) for environment variables and per-service layout.

**Phase 6 scope:** `test_network_links.py` covers link API and validation; `test_link_reconcile.py` exercises **create → reconcile → `connected`** for local and WireGuard links with mocked agent/breakout-controller HTTP. Cross-host **data-plane** traffic still requires [manual runbooks](../tests/integration/README.md#manual-two-agent-wireguard-link-test-phase-6).

**Phase 7 / guards:** `services/compliance/tests/` (explorer, project aggregate, region lineage); `services/projects/tests/test_network_delete_guard.py`, `test_ipam.py` (pool delete).

Conventions:

- Mark tests with `@pytest.mark.integration`
- Require `HUY_E2E=1` (set automatically by `make test-integration`)
- Use ephemeral organizations where possible; tests clean up org + projects after mutation
- `@pytest.mark.requires_agent` skips when no connected libvirt agent exists

### PostgreSQL schema upgrades

Projects unit tests use **SQLite**; production Compose uses **PostgreSQL**. Column additions (e.g. `ip_pools.pool_kind`) are applied via `apply_schema_upgrades` on projects startup. After pulling schema changes, restart `projects` against existing volumes — or use `docker compose down -v` for a clean dev DB.

## CodeQL

See [operations/codeql.md](operations/codeql.md). CodeQL runs via [`.github/workflows/codeql.yml`](../.github/workflows/codeql.yml) (advanced setup). **Disable CodeQL default setup** in repo Settings or you will see a configuration error.

## Observability (optional)

Shared library: [`shared/huy_telemetry`](../shared/huy_telemetry). Unit tests set `OTEL_SDK_DISABLED=true`.

```bash
docker compose --profile observability up -d --build
```

See [operations/observability-stack.md](operations/observability-stack.md) and [phase8-observability.md](operations/phase8-observability.md).

## Adding tests for a new phase

1. Add service unit tests under `services/<name>/tests/`.
2. Extend the root `Makefile` `test-unit` target if a new package is added.
3. When the phase needs multiple running services, add tests under `tests/integration/<service>/`, add a `test-integration-<service>` Makefile target, and extend the CI integration matrix in `.github/workflows/ci.yml`.
