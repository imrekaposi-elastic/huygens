# Breakout controller (`huy-breakout-controller`)

Go service (port **8085**) for **WireGuard link planning** in Phase 6. Called only by
`projects` over the internal service token — not by operators or the browser.

## Responsibilities

| Endpoint | Purpose |
|----------|---------|
| `GET /health` | Liveness |
| `POST /v1/links/plan` | Build WG peer configs for a pairwise link (keys supplied by projects) |
| `POST /v1/links/revoke` | Called by projects when deleting **WireGuard** links (before agent breakout is disabled) |

Does **not** touch libvirt, JWT, or iptables. Same-hypervisor **`local`** links bypass
this service entirely.

## Run (Compose)

Included in root `docker-compose.yml`. Health: `http://localhost:8085/health`.

## Configuration

| Variable | Description |
|----------|-------------|
| `HUY_BREAKOUT_HOST` | Bind address (default `0.0.0.0:8085`) |
| `BREAKOUT_SERVICE_TOKEN` | Must match `projects` `BREAKOUT_SERVICE_TOKEN` |

## Tests

No Go unit tests in-tree yet. Behavior is covered indirectly by projects unit tests
(mock HTTP) and manual two-agent validation — see
[docs/operations/phase6-release-and-validation.md](../../docs/operations/phase6-release-and-validation.md).
