# CodeQL (code scanning)

This repository uses GitHub **CodeQL default setup** (configured under **Settings → Code security → Code scanning**). Do not add a custom `.github/workflows/codeql.yml` that runs `github/codeql-action/init` / `analyze` while default setup is enabled — GitHub rejects the SARIF upload with:

> CodeQL analyses from advanced configurations cannot be processed when the default setup is enabled

## Languages

Enable only languages we ship:

| Language | Location |
|----------|----------|
| Python | `services/`, `agents/` |
| JavaScript / TypeScript | `web/` |
| Go | `services/breakout-controller/` |

Do **not** enable **C/C++**. There is no application C/C++ source; a committed virtualenv once caused autobuild to index vendored `.h` files and fail.

In default setup, open **CodeQL analysis → Edit** and uncheck C/C++ if it appears.

## Path exclusions

[`.github/codeql/codeql-config.yml`](../../.github/codeql/codeql-config.yml) is picked up by default setup (`paths-ignore` for venvs, `node_modules`, caches, etc.).

## Switching to an advanced (workflow) setup

If you need a repo-owned workflow (e.g. pinned matrix, custom build steps):

1. **Settings → Code security → Code scanning → CodeQL analysis → Disable CodeQL** (turn off default setup).
2. Add `.github/workflows/codeql.yml` with explicit `languages` and `config-file`.
3. Push and confirm the workflow uploads SARIF successfully.

You cannot run both default setup and an advanced workflow.

## Local / CI Python

Use `make venv` or your own venv — never commit `.venv-ci-sim/` or other environment directories (see root `.gitignore`).
