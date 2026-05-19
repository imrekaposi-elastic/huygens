# ADR 0008: OpenTelemetry and EDOT

## Status

Accepted (Phase 0)

## Context

FRAMEWORK_PLAN requires OpenTelemetry throughout, EDOT-friendly export for Elastic Observability customers.

## Decision

- All control-plane services instrumented with OTel (traces, metrics, logs).
- Export via **OTLP** (gRPC/HTTP) — no proprietary Elastic agent required in Huygens.
- Document **EDOT Collector** as recommended path to Elasticsearch/Kibana.
- Standard resource attributes:

| Attribute | Example |
|-----------|---------|
| `service.name` | `huy-registry` |
| `huy.org.id` | UUID |
| `huy.agent.id` | UUID |
| `huy.project.id` | UUID |

- Logs: structlog → **ECS JSON**; include `trace.id` for correlation.

Agent today: FastAPI instrumentation + OTLP traces; extend in Phase 8.

## Consequences

- Air-gapped docs include EDOT collector offline install.
- Kibana APM/Observability optional, not mandatory for core VM operations.
