# Testing strategy

## Unit tests (CI today)

Run all control-plane unit tests from the repo root:

```bash
make test
```

This executes pytest in each service:

| Service | Directory |
|---------|-----------|
| IAM | `services/iam` |
| Registry | `services/registry` |
| Inventory | `services/inventory` |
| Projects | `services/projects` |

Agent unit tests: `make -C agents/libvirt test`.

Each service uses in-memory SQLite, mocked HTTP (respx where needed), and synthetic JWTs signed with a test secret.

## Integration tests (future pipeline)

Full **cross-phase** tests (IAM → registry → projects → agent, or inventory poller against a real agent) are **not** part of the default `make test` job yet.

Planned layout:

```
tests/integration/
  README.md          # prerequisites, compose profile
  conftest.py        # shared fixtures, pytest marker integration
  test_phase0_3.py   # smoke: auth, register agent, create project, proxy list vms
```

Conventions:

- Mark tests with `@pytest.mark.integration`
- Run via `pytest -m integration` only when `docker compose` stack (or `HUY_E2E=1`) is up
- Keep unit and integration jobs separate in GitHub Actions so PRs stay fast

Example future workflow job:

```yaml
jobs:
  unit:
    run: make test
  integration:
    if: github.event_name == 'schedule' || contains(github.event.pull_request.labels.*.name, 'run-integration')
    run: docker compose up -d --build && pytest -m integration tests/integration
```

## Adding tests for a new phase

1. Add service unit tests under `services/<name>/tests/`.
2. Extend `Makefile` `test-unit` target.
3. When the phase needs multiple running services, add a skipped-by-default integration module under `tests/integration/`.
