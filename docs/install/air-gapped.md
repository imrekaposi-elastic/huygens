# Air-gapped installation

Huygens is designed for environments without outbound internet access. This guide
covers Phase 0–1 expectations; full Helm/offline bundles ship in Phase 10.

## Principles

- No mandatory telemetry or license call-home.
- All control-plane components run on your network.
- Agents talk only to your registry/inventory URLs (or local config until enrolled).

## Prerequisites (on-site)

| Component | Required | Notes |
|-----------|----------|--------|
| PostgreSQL 15+ | Yes | IAM, registry, inventory SoR |
| Kafka 3.x | Phase 1+ | Optional for poll-only MVP |
| Elasticsearch 8.x | Optional | Audit/compliance views (ECS) |
| Container runtime or Python 3.11+ | Yes | Per component README |

## Offline artifact bundle (target layout)

```
huygens-offline-<version>/
  images/           # OCI tarballs (registry, iam, inventory, agent)
  charts/           # Helm chart (Phase 10)
  python-wheels/    # Optional pip offline index
  schemas/          # Kafka JSON schemas (copy from repo)
  docs/             # This guide + architecture ADRs
```

Build images on a connected build host, transfer via removable media or internal registry mirror.

## Agent (hypervisor host)

1. Copy `agents/libvirt` tree or wheel to host.
2. Install: `pip install -e ".[libvirt]"` (or offline wheel).
3. Configure `/etc/huy-libvirt-agent/env` — no external URLs until enrolled.
4. `platform_admin` registers agent in registry, exports token OOB, sets `AGENT_TOKEN` on host.
5. Point `REGISTRY_URL` at internal registry service (Phase 1).

## Control plane (minimal Phase 1)

1. Deploy PostgreSQL; run migrations (Phase 1).
2. Deploy `services/iam`, `services/registry`, `services/inventory` on internal network.
3. Configure OTLP to on-site collector (EDOT or vanilla OTel Collector) — optional.
4. If using Elasticsearch: deploy EDOT collector with offline Elastic artifacts; index audit with ECS.

## Verification checklist

- [ ] Agent health: `GET /health` on hypervisor
- [ ] Registry lists agent after enrollment
- [ ] Inventory poll returns VMs without internet egress
- [ ] No outbound connections from agent except configured registry/inventory URLs
- [ ] Audit events visible in PG and (if enabled) ES

## Degraded mode

Without Kafka: inventory poller uses HTTP only (30s default, min 10s).

Without Elasticsearch: audit retained in PostgreSQL; export via API.

See [ADR 0009](../architecture/adrs/0009-air-gapped-install.md).
