# Phase 10 — Observability depth (logs & Prometheus)

**Status:** Planned (not started).

Phase **8** delivered the **OpenTelemetry + EDOT foundation** (traces, service map dependencies, audit in ES). Phase **10** extends the same Elastic stack with **operational logs** and **Prometheus-style metrics** in Kibana — not only trace-derived TPM/latency. (Phase **9** is audited VM SSH — see [PHASED_PLAN](../PHASED_PLAN.md).)

Normative context: [ADR 0008](../architecture/adrs/0008-opentelemetry-and-edot.md) (three channels); completed rollout: [phase8-observability.md](phase8-observability.md).

## Goals

| Goal | Outcome |
|------|---------|
| **Logs in Observability** | Control-plane (and optionally agent) stdout / ECS JSON visible in Kibana **Logs**, correlated with `trace.id` where possible |
| **Prometheus in Elastic** | Scrape libvirt agent **`GET /metrics`** (and optional service metrics) into Elasticsearch for dashboards / Infrastructure-style views |
| **Single stack** | Reuse observability Compose profile (EDOT collector + ES + Kibana); extend collector config, not a second monitoring product |

## Out of scope (Phase 10)

- Replacing PostgreSQL or audit Kafka with logs-only pipelines
- Full SIEM / security analytics pack
- Console VM/hypervisor charts (optional stretch — was P8-6; can ship in Phase 10 or later UI phase)
- EDOT SDK migration (apps stay on upstream OTel SDK + OTLP)

## Work packages (proposed)

### P10-1 — Application logs ingest

- **Option A:** OTLP logs from `huy_telemetry` (structlog → OTel Logs bridge) when `OTEL_EXPORTER_OTLP_ENDPOINT` is set
- **Option B:** EDOT **filelog** / Docker container log receiver → collector → ES (`logs-*otel*`)
- Correlate with traces via `trace.id` / `service.name` (already on ECS structlog fields)
- Document data view and Discover vs **Observability → Logs**

### P10-2 — Prometheus scrape (agents)

- EDOT collector **prometheus** receiver (or Elastic Agent integration) targeting:
  - Libvirt agent `http://<agent>:9100/metrics` (per ADR 0006; poll path via registry/inventory)
  - Optional: control-plane `/metrics` if exposed later
- Align scrape interval with inventory poll (**30s** default, **10s** min) per [PHASED_PLAN](../PHASED_PLAN.md)
- Map labels: `huy.agent.id`, `huy.org.id`, `huy.project.id` where available from target discovery

### P10-3 — Metrics UX

- Kibana dashboards or OTel content packs for host/VM CPU, memory, disk, network
- Link from console to Kibana when `HUY_OBSERVABILITY_KIBANA_URL` (or equivalent) is configured
- Clarify difference vs **trace-derived APM metrics** (TPM, latency) from Phase 8

### P10-4 — Docs & air-gap

- Extend [edot-integration.md](edot-integration.md) and [air-gapped install](../install/air-gapped.md) with logs + Prometheus receiver config
- Customer runbook: minimum resources, ports, retention

## Dependencies

- **Phase 8 ✅** — OTLP traces, EDOT gateway, `huy_telemetry`, observability profile
- **Phase 1** — inventory poller knows agent endpoints for Prometheus targets
- **Phase 5** — console deep-links (optional)

## Acceptance criteria

1. With `--profile observability`, operator can open **Observability → Logs** and filter `service.name:huy-compliance` (or equivalent) on control-plane stdout logs.
2. Libvirt agent Prometheus metrics appear in ES (or Kibana Infrastructure/metrics views) for at least one enrolled agent on the dev stack.
3. Documentation describes Phase 8 vs Phase 10 boundaries; no expectation that Phase 8 alone delivers Prometheus dashboards.

## References

- [observability-stack.md](observability-stack.md)
- [Elastic EDOT collector — Prometheus receiver](https://www.elastic.co/docs/reference/edot-collector/components/prometheusreceiver)
- [Elastic — host metrics](https://www.elastic.co/docs/reference/edot-collector/config/default-config-standalone)
