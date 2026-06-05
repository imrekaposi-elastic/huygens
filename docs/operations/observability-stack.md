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
| Logstash | (internal) | Kafka → data streams `huy-sessions`, `huy-audit` (ECS ingest pipelines + ILM) |

Customer / production EDOT options: [edot-integration.md](edot-integration.md).

## Memory

Approve ~**3 GB** extra on the Docker host: Elasticsearch `mem_limit: 2g` (1g heap), plus Kibana, Logstash, and collector.

Pinned in [compose.env.example](../../compose.env.example): `ELASTIC_STACK_VERSION=9.4.1`, `EDOT_COLLECTOR_VERSION=9.4.1`, `ELASTIC_PASSWORD`, and OTLP export (`OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317`). Compose defaults match if `.env` is omitted (except secrets).

Kibana encryption keys for Streams/alerts live in [`docker/observability/kibana/kibana.yml`](../../docker/observability/kibana/kibana.yml) (dev-only; rotate for production).

### Kibana login (required for Streams / Observability)

Kibana 9 **Streams** and **Observability** need Elasticsearch security enabled and a logged-in user with privileges. The dev profile enables minimal security:

| Setting | Default |
|---------|---------|
| User | `elastic` |
| Password | `changeme-dev-only` (override with `ELASTIC_PASSWORD` in `.env`) |

1. Open Kibana at **http://127.0.0.1:5601** (or `http://localhost:5601` — pick one host and stick to it).
2. Log in with the credentials above.
3. Then open **Streams** or **Observability**.

If you previously ran this profile with security **disabled**, reset the Elasticsearch volume once so passwords bootstrap cleanly:

```bash
# Stop observability services only (keeps Postgres/Kafka/etc. running if desired)
docker compose --profile observability down

# Remove ES data volume (name may be huygens_huygens-esdata on some installs)
docker volume ls | grep esdata
docker volume rm huygens_huygens-esdata   # adjust name from ls output

# Ensure .env has ELASTIC_PASSWORD (see compose.env.example), then:
docker compose --profile observability up -d
```

If you still see an auth redirect loop after login, clear site data for the Kibana host (delete the `sid` cookie) or use a private window.

## Audit events in Kibana

1. Perform a compliance or IAM change in the console.
2. Open Kibana → **Discover** → data view `huy-audit` (not legacy `huy-audit-*`).
3. Filter `event_kind: audit` or `audit_action: *`.

Audit remains **durable in PostgreSQL** first; Kafka + ES is the search plane ([ADR 0004](../architecture/adrs/0004-kafka-event-bus.md)). SSH sessions use:

| Kafka topic | Data stream | Content |
|-------------|-------------|---------|
| `huy.session.events` | `huy-sessions` | Session metadata (open/close), ECS |
| `huy.session.recording` | `huy-sessions` | Terminal I/O lines (`event.dataset: huy.session.terminal`) |
| `huy.audit.events` | `huy-audit` | Compliance audit events, ECS |

Ingest pipelines, ILM policies, and data streams are installed by `elasticsearch-setup` ([`docker/observability/elasticsearch/`](../../docker/observability/elasticsearch/)). Deleting a data stream in Kibana/ES Dev Tools is safe — rerun setup or ingest new events to recreate it.

### SSH sessions in Kibana

1. Connect to a VM and disconnect (terminal lines are published **on disconnect** only).
2. Open **Discover** → data view **Huy SSH Sessions** (`huy-sessions`).
3. Filter one session: `session.id: "<uuid>"` (copy from Console → Access → Sessions).

| Docs | Filter |
|------|--------|
| Start / end | `event.action: session.open` or `session.close` |
| Keystrokes | `event.action: session.terminal and terminal.input: *` |
| Shell output | `event.action: session.terminal and terminal.output: *` |

Correlate metadata and terminal lines with **`session.id`**.

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

Use offline Elastic artifacts and a customer-managed EDOT collector; see [air-gapped install](../install/air-gapped.md). This profile is **dev/demo only** (minimal security with `ELASTIC_PASSWORD` in `.env`).
