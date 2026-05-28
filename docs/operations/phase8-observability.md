# Phase 8 — OpenTelemetry rollout

Operational guide for Huygens observability (Phase 8). Normative decisions live in [ADR 0008](../architecture/adrs/0008-opentelemetry-and-edot.md).

## Three telemetry channels

| Channel | Purpose | System of record | Export |
|---------|---------|------------------|--------|
| **Audit** | Who changed what (compliance, IAM, registry) | PostgreSQL (+ optional Kafka) | `huy.audit.events` → Elasticsearch (`huy-audit-*`) |
| **Operational logs** | Debug, pollers, errors | stdout (structlog JSON) | ECS fields; optional OTLP logs later |
| **OTel signals** | Traces, metrics, SRE | Collector / Elastic Observability | OTLP gRPC or HTTP |

Audit must never depend on OTLP delivery alone. Use `trace.id` on audit mirrors for correlation.

## Environment variables

| Variable | Required | Example | Notes |
|----------|----------|---------|-------|
| `OTEL_SERVICE_NAME` | Recommended | `huy-registry` | Falls back to argument in `configure_otel()` |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | For export | `http://otel-collector:4317` | Unset = no OTLP (local/tests) |
| `OTEL_EXPORTER_OTLP_PROTOCOL` | No | `grpc` or `http/protobuf` | Default `grpc` |
| `OTEL_RESOURCE_ATTRIBUTES` | No | `huy.org.id=<uuid>` | Comma-separated `key=value` |
| `OTEL_SDK_DISABLED` | Tests | `true` | Disables SDK and auto-instrumentation |

Per-service names: `huy-iam`, `huy-registry`, `huy-inventory`, `huy-projects`, `huy-compliance`, `huy-breakout-controller`, `huy-libvirt-agent`.

## Shared library

[`shared/huy_telemetry`](../../shared/huy_telemetry) — use in every control-plane FastAPI service:

1. `prepare_service_telemetry(service_name=...)` — structlog ECS + tracer + httpx
2. `attach_fastapi_telemetry(app, export_enabled=...)` — middleware + FastAPI spans

## Local stack

- Default control plane: `docker compose up -d --build`
- With Elasticsearch + collector: `docker compose --profile observability up -d --build` — see [observability-stack.md](observability-stack.md)

Uncomment in `.env`:

```bash
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317
OTEL_EXPORTER_OTLP_PROTOCOL=grpc
```

## Rollout status

| Component | OTel traces/metrics | ECS structlog | Notes |
|-----------|-------------------|---------------|-------|
| registry, iam, inventory, projects, compliance | P8-1 / P8-3 | Yes | Audit Kafka includes `trace_id` where applicable |
| libvirt agent | P8-4 | Yes | OTLP traces + host/VM metrics; ECS structlog; `/metrics` Prometheus unchanged |
| breakout-controller (Go) | P8-5 | Planned | |

## Libvirt agent (hypervisor)

Runs on the KVM host (not in Compose). Install with `pip install -e ".[libvirt]"` from `agents/libvirt` (pulls `huy-telemetry`).

| Signal | Endpoint / mechanism |
|--------|----------------------|
| Traces | FastAPI auto-instrumentation; `GET /healthz` is traced |
| Metrics (pull) | `GET /metrics` (Prometheus) |
| Metrics (push) | OTLP gauges synced on `HUY_STATUS_POLL_SECONDS` when `OTEL_EXPORTER_OTLP_ENDPOINT` is set |
| Logs | structlog JSON with ECS correlation fields |

Resource attributes include `huy.agent.country`, `huy.agent.city`, `huy.agent.company` (from agent enrollment labels).

## EDOT / production

Customer-facing Elastic path: [EDOT integration](edot-integration.md) (P8-5b). Air-gap: [install/air-gapped.md](../install/air-gapped.md).
