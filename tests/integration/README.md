# Cross-service integration tests

Black-box tests against a **running** Docker Compose stack. They validate JWT propagation,
org/project/IPAM workflows, inventory SSE, and (optionally) the projects agent proxy.

## Prerequisites

```bash
cp compose.env.example .env
docker compose up -d --build
```

Default credentials match `compose.env.example`: `platform-admin` / `platform-admin-dev`.

## Run

```bash
make test-integration
```

Or manually:

```bash
cd tests/integration
python3 -m pip install -e ".[dev]"
HUY_E2E=1 python3 -m pytest -q
```

Unit tests (`make test`) **do not** run these; they stay fast for PR CI.

## Environment

| Variable | Default | Purpose |
|----------|---------|---------|
| `HUY_E2E` | unset | Must be `1` to run `@pytest.mark.integration` tests |
| `HUY_IAM_URL` | `http://127.0.0.1:8081` | IAM base URL |
| `HUY_REGISTRY_URL` | `http://127.0.0.1:8082` | Registry base URL |
| `HUY_INVENTORY_URL` | `http://127.0.0.1:8083` | Inventory base URL |
| `HUY_PROJECTS_URL` | `http://127.0.0.1:8084` | Projects base URL |
| `HUY_WEB_URL` | `http://127.0.0.1:5173` | Console nginx base URL |
| `HUY_E2E_USER` | `platform-admin` | Bootstrap login username |
| `HUY_E2E_PASSWORD` | `platform-admin-dev` | Bootstrap login password |
| `HUY_E2E_ORG_ID` | first org listed | Org for dashboard/agent tests |

## Test layout

| Module | Scope |
|--------|--------|
| `test_stack_health.py` | `/health` on all services + console → IAM login proxy |
| `test_auth_cross_service.py` | Login, `/me`, 401 without JWT, JWT on registry/inventory/projects |
| `test_operator_workflow.py` | Ephemeral org → project → IPAM pool → wizard (cleanup after test) |
| `test_inventory_live.py` | Dashboard, SSE Bearer-only contract, nginx SSE proxy |
| `test_agent_proxy.py` | `@pytest.mark.requires_agent` — list VMs/networks via projects proxy |

Tests marked `requires_agent` skip automatically when no agent is `connected` for the target org.

## CI recommendation

Keep `make test` on every PR. Run `make test-integration` on a schedule or when the PR has label `run-integration`, after `docker compose up -d --build`.
