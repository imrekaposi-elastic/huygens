# EDOT integration (Elastic Observability)

Huygens exports **standard OTLP** (traces and metrics) from every control-plane service and the libvirt agent. No Elastic-proprietary agent is required in application code. For **Kibana Applications**, **service map**, and **transaction** views, route OTLP through the **Elastic Distribution of OpenTelemetry (EDOT) Collector**, which adds the `elasticapm` processor and connector that contrib collectors do not ship.

Normative decisions: [ADR 0008](../architecture/adrs/0008-opentelemetry-and-edot.md). Local stack: [observability-stack.md](observability-stack.md). **Phase 8** covers traces and service-map dependencies; **application logs** and **Prometheus scrape** are [Phase 10](phase10-observability-logs-and-prometheus.md).

## Architecture

```text
Huygens services (OTLP SDK)
        │  gRPC :4317 or HTTP :4318
        ▼
EDOT Collector (gateway)
  • batch
  • elasticapm processor  → APM-compatible trace fields
  • elasticapm connector  → pre-aggregated service metrics
        │
        ▼
Elasticsearch (mapping.mode: otel data streams)
        │
        ▼
Kibana Observability → Applications / Service map / Traces
```

| Path | Collector | Kibana Applications / service map |
|------|-----------|-----------------------------------|
| **Recommended (customer + local dev)** | EDOT Collector | Yes (with traffic + time range) |
| Contrib collector → ES (`mapping.mode: otel`) | `otel-collector.yaml` (legacy sample) | No — use **Discover** on `traces-*otel*` |
| Elastic Cloud **Managed OTLP** | None at edge (mOTLP enriches server-side) | Yes |
| APM Server OTLP intake | Optional alternative | Yes |

## Application configuration (unchanged)

Huygens services only need OTLP environment variables ([phase8-observability.md](phase8-observability.md)):

```bash
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317   # Compose service name
OTEL_EXPORTER_OTLP_PROTOCOL=grpc
OTEL_SERVICE_NAME=huy-registry   # per service
```

On a hypervisor or customer network, point `OTEL_EXPORTER_OTLP_ENDPOINT` at the EDOT gateway hostname (or Elastic Agent / Fleet policy endpoint).

Resource attributes (`huy.org.id`, `huy.agent.id`, …) are set per [ADR 0008](../architecture/adrs/0008-opentelemetry-and-edot.md).

## Local dev (Compose observability profile)

The `observability` profile runs the **EDOT Collector** image aligned with the Elastic stack version:

```bash
cp compose.env.example .env
# Uncomment OTLP lines in .env, then:
docker compose --profile observability up -d --build
```

| Setting | Default | Purpose |
|---------|---------|---------|
| `ELASTIC_STACK_VERSION` | `9.4.1` | Elasticsearch, Kibana, Logstash |
| `EDOT_COLLECTOR_VERSION` | `9.4.1` | `docker.elastic.co/elastic-agent/elastic-otel-collector` |
| `ELASTIC_API_KEY` | empty | Dev ES has security disabled; set for production |

Collector config: [`docker/observability/edot-collector-gateway.yaml`](../../docker/observability/edot-collector-gateway.yaml) (derived from [Elastic gateway sample](https://github.com/elastic/elastic-agent/blob/v9.4.1/internal/edot/samples/linux/gateway.yml)).

After changing collector config:

```bash
docker compose --profile observability up -d --force-recreate otel-collector
```

## Kibana: Applications and service map

1. **Confirm ingest** — traces and derived metrics in Elasticsearch:
   ```bash
   curl -s 'http://127.0.0.1:9200/_cat/indices/*otel*?v'
   ```
2. **Generate cross-service traffic** — the service map needs **linked spans** (caller → callee). Hitting each service’s `/health` alone only shows isolated nodes. Use the console (IAM → projects → registry) or any workflow that triggers httpx calls between services (`huy_telemetry` instruments httpx).
3. Open **Kibana** → **Observability** → **Applications** (or **Services**).
4. Set time range to **Last 15 minutes** (or since you generated traffic).
5. Open **Service map** for a service that appears in the list.

### OpenTelemetry content packs (optional dashboards)

For OTel-native dashboards (host, Kubernetes, RUM, etc.), install assets from **Kibana → Integrations** (search “OpenTelemetry”). This is optional for the core **Applications / service map** experience when using EDOT gateway ingest.

On air-gapped sites, ship integration packages offline; see [air-gapped install](../install/air-gapped.md).

## Production and Elastic Cloud

### Self-managed Elasticsearch (secured)

1. Deploy EDOT Collector 9.x on a gateway host (VM, K8s, or sidecar).
2. Create an Elasticsearch API key with ingest privileges for OTel data streams.
3. Set environment variables (or substitute in config):
   ```bash
   ELASTIC_ENDPOINT=https://elasticsearch.example.com:9200
   ELASTIC_API_KEY=<base64-api-key>
   ```
4. Use TLS on OTLP receivers and between collector and Elasticsearch ([Elastic docs](https://www.elastic.co/docs/reference/edot-collector/config/default-config-standalone#secure-the-connection-between-the-edot-collector-and-elastic)).
5. Point all Huygens `OTEL_EXPORTER_OTLP_ENDPOINT` values at the gateway.

Pin **EDOT Collector** to the same major.minor as your Elastic Stack ([compatibility matrix](https://www.elastic.co/docs/reference/opentelemetry/compatibility/collectors)).

### Elastic Cloud Serverless / Hosted — Managed OTLP (mOTLP)

Send OTLP directly to the project **Managed OTLP endpoint**; Elastic enriches traces server-side (no `elasticapm` components at the edge). Configure:

```bash
OTEL_EXPORTER_OTLP_ENDPOINT=https://<project>.otel.elastic.cloud:443
OTEL_EXPORTER_OTLP_HEADERS="Authorization=ApiKey <key>"
```

See [Managed OTLP Endpoint](https://www.elastic.co/docs/reference/opentelemetry/motlp).

### Elastic Agent as collector

From Elastic Stack 9.2+, Fleet can run the embedded EDOT Collector (`elastic-agent otel`). Use when you already standardize on Fleet for edge collection; Huygens apps still speak plain OTLP.

## Air-gapped

Bundle the `elastic-otel-collector` image and config YAML in your offline artifact set. Applications continue to use OTLP only. See [air-gapped install](../install/air-gapped.md).

## Troubleshooting

| Symptom | Check |
|---------|--------|
| Empty Applications / service map | Collector image is **EDOT** (`elastic-otel-collector`), not `otel-collector-contrib`; config includes `elasticapm` processor + connector |
| Traces in Discover but not Applications | Same as above — contrib → ES is Discover-only |
| Services listed, empty service map | No cross-service traces; generate real request chains |
| Postgres / Kafka / SeaweedFS not on service map | **SQLAlchemy** → `peer.service=postgresql`; **Kafka** publishes → `peer.service=kafka`; **compliance** S3 evidence/export I/O → `peer.service=seaweedfs` (override with `OTEL_PEER_OBJECT_STORE_SERVICE_NAME`). Generate traffic that hits DB, publishes audit/events, or uploads/downloads evidence. Dependencies are edges from app services, not standalone OTLP services. |
| Collector errors on export | `docker logs <otel-collector-container>`; verify `ELASTIC_ENDPOINT` and `ELASTIC_API_KEY` when security is on |
| Version skew | Match `EDOT_COLLECTOR_VERSION` to `ELASTIC_STACK_VERSION` (9.4.x with 9.4.x) |

## References

- [Elastic EDOT](https://www.elastic.co/docs/reference/opentelemetry)
- [EDOT Collector gateway config](https://www.elastic.co/docs/reference/edot-collector/config/default-config-standalone#gateway-mode)
- [elasticapm processor](https://www.elastic.co/docs/reference/edot-collector/components/elasticapmprocessor)
- [elasticapm connector](https://www.elastic.co/docs/reference/edot-collector/components/elasticapmconnector)
- [OpenTelemetry with Elastic APM](https://www.elastic.co/docs/solutions/observability/apm/opentelemetry)
