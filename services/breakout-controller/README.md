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
| `OTEL_SERVICE_NAME` | Default `huy-breakout-controller` |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | OTLP collector URL (unset = traces/metrics in-process only) |
| `OTEL_EXPORTER_OTLP_PROTOCOL` | `grpc` (default) or `http/protobuf` |
| `OTEL_RESOURCE_ATTRIBUTES` | Extra resource labels (`key=value`, comma-separated) |
| `OTEL_SDK_DISABLED` | `true` in unit tests |

HTTP responses include `X-Request-Id` and `X-Trace-Id` when a span is active ([ADR 0008](../../docs/architecture/adrs/0008-opentelemetry-and-edot.md)).

## Tests

```bash
make test
# or from repo root: make test-breakout-controller
```

Covers `/health`, service-token auth, `POST /v1/links/plan` (validation + peer config), `POST /v1/links/revoke`, interface name sanitization, and WireGuard key generation. Projects tests additionally mock HTTP against this API.
