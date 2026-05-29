# Local observability stack (Elasticsearch + EDOT Collector)

Optional Compose profile for **Phase 8** (OTLP traces + EDOT) and Elastic-customer demos. **Phase 10** will extend the same profile for logs ingest and Prometheus scrape — see [phase10-observability-logs-and-prometheus.md](phase10-observability-logs-and-prometheus.md). **Not required** for core VM operations.

## Start

```bash
cp compose.env.example .env
docker compose --profile observability up -d --build
```

Default stack (IAM, registry, compliance, …) starts as usual. The profile adds:

| Service | URL | Purpose |
|---------|-----|---------|
| Elasticsearch | http://127.0.0.1:9200 | Search / storage |
| Kibana | http://127.0.0.1:5601 | **Observability → Applications**, Discover, audit |
| EDOT Collector (`otel-collector`) | OTLP gRPC `4317`, HTTP `4318` | `elastic-otel-collector` — `elasticapm` processor + connector |
| Logstash | (internal) | `huy.audit.events` → `huy-audit-*` indices |

Customer / production EDOT options: [edot-integration.md](edot-integration.md).

## Memory

Approve ~**3 GB** extra on the Docker host: Elasticsearch `mem_limit: 2g` (1g heap), plus Kibana, Logstash, and collector.

Pinned in [compose.env.example](../../compose.env.example): `ELASTIC_STACK_VERSION=9.4.1`, `EDOT_COLLECTOR_VERSION=9.4.1`. Compose defaults match if `.env` is omitted.

## Audit events in Kibana

1. Perform a compliance or IAM change in the console.
2. Open Kibana → **Discover** → data view `huy-audit-*` (create if prompted).
3. Filter `event_kind: audit` or `audit_action: *`.

Audit remains **durable in PostgreSQL** first; Kafka + ES is the search plane ([ADR 0004](../architecture/adrs/0004-kafka-event-bus.md)). SSH sessions use `huy.session.events` → `huy-sessions-*` ([ADR 0014](../architecture/adrs/0014-ssh-gateway-and-session-recording.md)).

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

After switching to the EDOT Collector image, recreate the collector once:

```bash
docker compose --profile observability up -d --force-recreate otel-collector
```

### Applications and service map (EDOT)

1. Confirm OTel data streams exist:
   ```bash
   curl -s 'http://127.0.0.1:9200/_cat/indices/*otel*?v'
   ```
   Expect names like `traces-generic.otel-default` and metrics streams from the `elasticapm` connector.
2. Generate **cross-service** traffic (console login, project flows, or any path that calls another service over HTTP). Per-service `/health` alone does not draw service-map edges.
3. Kibana → **Observability** → **Applications** → pick a service → **Service map**.
4. Time range: **Last 15 minutes**.

### Discover (raw traces)

Kibana → **Discover** → data view `traces-*otel*` → time field `@timestamp`. Use for ad-hoc span search; Applications UI is the primary APM experience with EDOT.

If indices are missing, check the collector: `docker logs huygens-otel-collector-1 2>&1 | tail -30` (no `index_not_found_exception`).

Legacy contrib collector config (Discover-only): [`docker/observability/otel-collector.yaml`](../../docker/observability/otel-collector.yaml).

## Air-gapped

Use offline Elastic artifacts and a customer-managed EDOT collector; see [air-gapped install](../install/air-gapped.md). This profile is **dev/demo only** (`xpack.security.enabled=false`).
