# ADR 0008: OpenTelemetry and EDOT

## Status

Accepted (Phase 0); amended Phase 8 (P8-0)

## Context

FRAMEWORK_PLAN requires OpenTelemetry throughout, EDOT-friendly export for Elastic Observability customers.

## Decision

### Signals

- All control-plane services instrumented with OTel **traces** and **metrics**.
- Export via **OTLP** (gRPC or HTTP) — no proprietary Elastic agent required in Huygens.
- Document **EDOT Collector** (or Elastic Agent with `ELASTIC_AGENT_OTEL`) as recommended path to Elasticsearch/Kibana Observability.
- **Operational logs:** structlog → **ECS-shaped JSON** on stdout; correlate with `trace.id` / `transaction.id`.
- **OTel logs** (OTLP) optional later; do not replace audit trail.

### Standard resource attributes

| Attribute | Example | When |
|-----------|---------|------|
| `service.name` | `huy-registry` | Always |
| `huy.org.id` | UUID | HTTP handlers when JWT carries org |
| `huy.agent.id` | UUID | Agent-scoped operations |
| `huy.project.id` | UUID | Project-scoped operations |

Set via `OTEL_RESOURCE_ATTRIBUTES` or `configure_otel(..., extra_resource={...})`.

### Environment contract

| Variable | Purpose |
|----------|---------|
| `OTEL_SERVICE_NAME` | Service identity (also passed to `configure_otel`) |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | Collector URL; unset disables export |
| `OTEL_EXPORTER_OTLP_PROTOCOL` | `grpc` (default) or `http/protobuf` |
| `OTEL_RESOURCE_ATTRIBUTES` | Extra resource labels (`key=value`, comma-separated) |
| `OTEL_SDK_DISABLED` | `true` in unit tests |

### Log field mapping (ECS-oriented)

| Field | Source |
|-------|--------|
| `service.name` | Service name at startup |
| `@timestamp` | ISO-8601 UTC |
| `log.level` | structlog level |
| `trace.id` | Active OTel span (32 hex) |
| `transaction.id` | Active span id (16 hex) |
| `http.request.id` | `X-Request-Id` middleware |

Implemented in [`shared/huy_telemetry`](../../../shared/huy_telemetry).

### Audit vs OTel (three channels)

1. **Audit trail** — `record_audit()` → PostgreSQL; mirror to Kafka `huy.audit.events` for Elasticsearch. Include `trace.id` when a span is active. **No sampling** on audit; never rely on OTLP alone.
2. **Operational logs** — structlog via `configure_structlog_ecs`.
3. **OTel signals** — traces/metrics via OTLP to collector (dev: Compose `otel-collector`; prod: EDOT).

### Implementation

- Shared package: `shared/huy_telemetry` (FastAPI + httpx instrumentation).
- Libvirt agent: existing `telemetry.py` aligned in Phase 8; keep Prometheus `/metrics` (ADR 0006).
- Go breakout-controller: OTel SDK in Phase 8.

Agent today: FastAPI instrumentation + OTLP traces; registry pilot uses `huy_telemetry` (Phase 8).

## Consequences

- Air-gapped docs include EDOT collector offline install.
- Kibana APM/Observability optional, not mandatory for core VM operations.
- Tests set `OTEL_SDK_DISABLED=true` and leave `OTEL_EXPORTER_OTLP_ENDPOINT` unset unless testing export.

## References

- [phase8-observability.md](../../operations/phase8-observability.md)
- [observability-stack.md](../../operations/observability-stack.md)
- [Elastic EDOT](https://www.elastic.co/docs/reference/opentelemetry)
