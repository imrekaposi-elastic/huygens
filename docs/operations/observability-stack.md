# Local observability stack (Elasticsearch + EDOT-friendly OTLP)

Optional Compose profile for Phase 8 prep and Elastic-customer demos. **Not required** for core VM operations.

## Start

```bash
cp compose.env.example .env
docker compose --profile observability up -d --build
```

Default stack (IAM, registry, compliance, …) starts as usual. The profile adds:

| Service | URL | Purpose |
|---------|-----|---------|
| Elasticsearch | http://127.0.0.1:9200 | Search / storage |
| Kibana | http://127.0.0.1:5601 | Discover, APM (when OTLP wired in Phase 8) |
| OpenTelemetry Collector | OTLP gRPC `4317`, HTTP `4318` | `otel/opentelemetry-collector-contrib` (pin `OTEL_COLLECTOR_VERSION`, default `0.153.0`) |
| Logstash | (internal) | `huy.audit.events` → `huy-audit-*` indices |

## Memory

Approve ~**3 GB** extra on the Docker host: Elasticsearch `mem_limit: 2g` (1g heap), plus Kibana, Logstash, and collector.

Pinned in [compose.env.example](../../compose.env.example): `ELASTIC_STACK_VERSION=9.4.1` (latest 9.4.x), `OTEL_COLLECTOR_VERSION=0.153.0`. Compose defaults match if `.env` is omitted.

## Audit events in Kibana

1. Perform a compliance or IAM change in the console.
2. Open Kibana → **Discover** → data view `huy-audit-*` (create if prompted).
3. Filter `event_kind: audit` or `audit_action: *`.

Audit remains **durable in PostgreSQL** first; Kafka + ES is the search plane ([ADR 0004](../architecture/adrs/0004-kafka-event-bus.md)).

## OTLP (Phase 8)

Uncomment in `.env` (see [compose.env.example](../../compose.env.example)):

```bash
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317
OTEL_EXPORTER_OTLP_PROTOCOL=grpc
```

Compose sets `OTEL_SERVICE_NAME` per service (`huy-iam`, `huy-registry`, `huy-inventory`, `huy-projects`, `huy-compliance`). Rebuild after code changes:

```bash
docker compose --profile observability up -d --build
```

Spot-check any control-plane port (8081–8086); each `/health` should return `X-Request-Id` and `X-Trace-Id`. Traces reach the collector only when `OTEL_EXPORTER_OTLP_ENDPOINT` is set.

## Air-gapped

Use offline Elastic artifacts and a customer-managed EDOT collector; see [air-gapped install](../install/air-gapped.md). This profile is **dev/demo only** (`xpack.security.enabled=false`).
