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
| `test_network_links.py` | Overlay pool + topology + link list API smoke (**no** POST link, **no** reconciler, **no** agent) |

Tests marked `requires_agent` skip automatically when no agent is `connected` for the target org.

Integration tests are **not** a substitute for manual Phase 6 validation. See [docs/operations/phase6-release-and-validation.md](../docs/operations/phase6-release-and-validation.md).

## Manual two-agent WireGuard link test (Phase 6)

Requires **two connected libvirt agents** in the same organization, each with a project-managed vnet (not `default`) and **up-to-date libvirt agent** builds.

1. Create an **overlay pool** under **IPAM** (`pool_kind: overlay`), e.g. `10.255.0.0/24`.
2. Assign a vnet on agent A to project P1 and a vnet on agent B to project P2 (console **Projects** → networks). Both need IPv4 CIDRs (IPAM or network create).
3. Open **Topology**, connect vnet A to vnet B (drag or click source then target). Select overlay pool when prompted.
4. Wait for link status **connected** (reconciler ~15s). Edge shows tunnel `/30` addresses; `link_type` is `wireguard`.
5. From a VM on vnet A, ping a VM on vnet B across the WireGuard breakout.
6. Delete the link in the topology detail panel; verify breakout disabled on both agents (`GET` via projects proxy if needed).

**Single-agent org:** cross-agent link API calls may succeed but status stays **`error`** until a second agent is connected — expected.

## Manual same-hypervisor local link test (Phase 6)

Requires **one connected agent** with two vnets on **different projects** (or same org), each with an IPv4 CIDR.

1. Open **Topology** — both vnets appear on the same agent node grouping.
2. Connect vnet A to vnet B. Modal should say **same hypervisor** / direct routing — **no** overlay pool picker.
3. Wait for **connected**. Edge label shows vnet CIDRs and `(local, …)`; API `link_type` is `local`.
4. From a VM on vnet A, ping a VM on vnet B (L2/routing on host via iptables, not WireGuard).
5. Delete the link; verify flat breakout cleared on both networks.

**Agent too old:** reconcile fails with HTTP 422 / `local_peer` not allowed — upgrade agent per [operations doc](../docs/operations/phase6-release-and-validation.md).

## Manual network delete (inventory orphan regression)

1. Create and assign a vnet; confirm it appears on dashboard and in project networks list.
2. Delete the vnet from **Projects → networks** (not only unassign).
3. After inventory poll (~30s), the vnet must **not** appear as unassigned/orphaned on the dashboard.
4. Topology must not list the vnet after assignment row is cleared.

## CI recommendation

Keep `make test` on every PR. Run `make test-integration` on a schedule or when the PR has label `run-integration`, after `docker compose up -d --build`.
