# Testing strategy

## Unit tests (default CI)

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
| Console | `web` (`npm test`) |

Shared packages `huy_auth` and `huy_events` are installed once via `make test-deps` before services that depend on them.

Each service uses in-memory SQLite, mocked HTTP (respx where needed), and synthetic JWTs signed with a test secret.

Agent unit tests: `make -C agents/libvirt test`.

## Integration tests (compose stack)

Cross-service tests live under `tests/integration/`. They are **not** part of `make test`.

```bash
docker compose up -d --build
make test-integration
```

See [tests/integration/README.md](../tests/integration/README.md) for environment variables and module layout.

Conventions:

- Mark tests with `@pytest.mark.integration`
- Require `HUY_E2E=1` (set automatically by `make test-integration`)
- Use ephemeral organizations where possible; tests clean up org + projects after mutation
- `@pytest.mark.requires_agent` skips when no connected libvirt agent exists

Example GitHub Actions job:

```yaml
jobs:
  unit:
    run: make test
  integration:
    if: github.event_name == 'schedule' || contains(github.event.pull_request.labels.*.name, 'run-integration')
    run: |
      docker compose up -d --build
      make test-integration
```

## Adding tests for a new phase

1. Add service unit tests under `services/<name>/tests/`.
2. Extend the root `Makefile` `test-unit` target if a new package is added.
3. When the phase needs multiple running services, extend `tests/integration/` and document any new env vars in `tests/integration/README.md`.
