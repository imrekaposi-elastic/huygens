# Contributing to Huygens

Thank you for contributing to Huygens. This project is open source under the
[Apache License 2.0](LICENSE).

## Before you start

- Read [FRAMEWORK_PLAN.md](FRAMEWORK_PLAN.md) for product scope.
- Read [docs/architecture/README.md](docs/architecture/README.md) for ADRs and diagrams.
- For Elastic employees: follow your internal open-source contribution policy and
  obtain OSPO/Legal review before public releases.

## Development setup

### Libvirt agent

```bash
cd agents/libvirt
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,libvirt]"
cp .env.example .env
make test
```

### Control plane services (Phase 1+)

Each service under `services/` has its own `README.md` and `pyproject.toml`.

```bash
cd services/registry   # example
pip install -e ".[dev]"
```

## Pull requests

1. Fork or branch from `main`.
2. Keep changes focused; match existing style (ruff, type hints).
3. Add or update tests for behavior changes.
4. Update ADRs in `docs/architecture/adrs/` when making architectural decisions.
5. Ensure CI passes (`make test` at repo root runs agent tests).

## Commit messages

Use clear, imperative subjects. Example:

```
Add registry agent enrollment API

Map agent tokens to organization_id; platform_admin export only.
```

## Code of conduct

See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
