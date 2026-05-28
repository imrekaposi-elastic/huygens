# CodeQL (code scanning)

This repository uses an **advanced (workflow) CodeQL setup** at [`.github/workflows/codeql.yml`](../../.github/workflows/codeql.yml). Languages: **Python**, **JavaScript/TypeScript**, **Go** only — **not C/C++** (there is no application C/C++ source; a committed `.venv-ci-sim/` once caused C++ autobuild to index vendored headers and fail).

## One-time GitHub setting (required)

If **CodeQL default setup** is still enabled in the repository, you will see **“Code scanning configuration error”** or SARIF upload failures. Default setup and this workflow cannot both run.

1. Open the repo on GitHub → **Settings** → **Advanced Security** (or **Code security**).
2. Under **Code scanning** → **CodeQL analysis** → **Disable** default setup (or switch off “Default” so only the workflow runs).
3. Push to `main` and confirm the **CodeQL** workflow completes under **Actions**.

Org-level default setup: an org owner may need to exclude this repo or turn off org-wide default CodeQL for it.

## Languages

| Language | Location | Build |
|----------|----------|--------|
| Python | `services/`, `agents/libvirt/src`, `shared/` | `build-mode: none` |
| JavaScript / TypeScript | `web/` | `npm ci` in workflow |
| Go | `services/breakout-controller/` | `go build ./...` |

Do **not** enable **C/C++** in any CodeQL UI.

## Path exclusions

[`.github/codeql/codeql-config.yml`](../../.github/codeql/codeql-config.yml) scopes `paths` and `paths-ignore` (venvs, `node_modules`, caches, etc.).

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| **Code scanning configuration error** on Security tab | Disable **default** CodeQL setup; rely on `.github/workflows/codeql.yml` only. Re-run failed analyses from **Actions**. |
| “CodeQL analyses from advanced configurations cannot be processed when the default setup is enabled” | Same — disable default setup. |
| C/C++ autobuild / “No source code was seen” | Uncheck C/C++ in default setup, or use this workflow (C++ not in matrix). Never commit `.venv-ci-sim/` (see root `.gitignore`). |
| **1 configuration not found** on a PR | Rebase on `main` after default setup is fixed; or re-enable default setup consistently on `main` and the PR branch. |

## Local / CI Python

Use `make venv` or your own venv — never commit `.venv-ci-sim/` or other environment directories.
