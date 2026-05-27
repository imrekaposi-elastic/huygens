# Phase 6 — release, deployment, and validation

Operational guide for **hybrid breakout and network linking** (Phase 6). Complements
[ADR 0012](../architecture/adrs/0012-hybrid-breakout-and-network-linking.md) and
[PHASED_PLAN.md](../PHASED_PLAN.md).

Phase 6 ships **control-plane features in Compose** and **data-plane behavior on each
libvirt hypervisor**. Treat both as one release.

## What “Phase 6 done” means

| Layer | MVP (shipped) | GA (not yet — see backlog) |
|-------|----------------|----------------------------|
| **Compose stack** | `projects`, `breakout-controller`, `web`, Kafka, overlay IPAM, topology UI, link reconciler | Automated link-reconcile integration test in CI |
| **Hypervisor agent** | WG + `local_peer` breakout when agent matches control-plane version | Capability negotiation; zero-touch upgrade |
| **Validation** | Unit tests + integration **API smoke**; manual two-agent WG runbook | Automated cross-host data-plane proof |
| **Events** | Publish to `huy.network.links` when topic exists | Topic auto-provisioned in Compose; ES consumer |

## Control plane vs hypervisor agent

```text
  docker compose (laptop/server)          KVM host (e.g. dommel)
  ┌─────────────────────────┐            ┌──────────────────────┐
  │ projects, inventory,    │  HTTPS     │ huy-libvirt-agent    │
  │ breakout-controller, web│ ────────►  │ (NOT in Compose)     │
  └─────────────────────────┘            └──────────────────────┘
```

After upgrading Compose images, **always upgrade agents** on every hypervisor that
participates in topology links. Skew causes reconcile errors (e.g. `local_peer` rejected
with HTTP 422).

### Agent upgrade checklist (per hypervisor)

1. Sync monorepo (or install matching wheel) to the version on `main`.
2. From `agents/libvirt`: `python3 -m pip install -e ".[libvirt]"`
3. `sudo systemctl restart huy-libvirt-agent`
4. Verify flat breakout accepts `local_peer`:

   ```bash
   python3 -c "from huy_libvirt_agent.api.schemas.network import FlatBreakoutConfig; \
   print(FlatBreakoutConfig.model_json_schema()['properties']['mode'])"
   ```

   Expected enum includes `local_peer`.

5. Reconcile stuck links in the console (**Topology** — links in `error` retry every ~15s).

See [agents/libvirt/README.md](../../agents/libvirt/README.md#upgrading-the-agent-phase-6).

### Control plane upgrade

```bash
docker compose up -d --build projects web breakout-controller
```

Existing PostgreSQL volumes: `projects` runs `apply_schema_upgrades` on startup (e.g.
`ip_pools.pool_kind`). Restart `projects` after pulling schema changes.

## Kafka topic `huy.network.links`

Projects publishes link lifecycle events to **`huy.network.links`** (not `huy.audit.events`).
See [ADR 0004](../architecture/adrs/0004-kafka-event-bus.md).

Apache Kafka in Compose does **not** auto-create application topics. Create once per cluster:

```bash
docker compose exec kafka /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server localhost:9092 \
  --create --if-not-exists \
  --topic huy.network.links \
  --partitions 1 \
  --replication-factor 1
```

Without this topic, projects logs `Topic huy.network.links not found`; link CRUD still works;
console refresh uses inventory SSE / polling, not link Kafka consumers.

## Manual validation

| Scenario | Runbook |
|----------|---------|
| Cross-hypervisor WireGuard link | [tests/integration/README.md](../../tests/integration/README.md#manual-two-agent-wireguard-link-test-phase-6) |
| Same-hypervisor local link | [tests/integration/README.md](../../tests/integration/README.md#manual-same-hypervisor-local-link-test-phase-6) |
| Network delete / inventory orphan | Delete via **Projects → networks**; agent removes libvirt + metadata; dashboard should not list ghost vnets after poll (~30s) |

## Known limitations (documented backlog)

These are **not** fixed by documentation alone; tracked for product planning:

- **Network delete** does not auto-delete `network_links` referencing that vnet (topology may show stale edges).
- **Out-of-band** hypervisor deletes do not prune `project_resources` (topology may show ghost nodes until unassign/delete in API).
- **`POST /v1/links/revoke`** on breakout-controller is implemented but unused; delete path disables breakout via agent proxy only.
- **Console** does not yet show link `config_drift` on the topology page (API field exists).
- **Flat L2** `bridge_uplink` / `macvlan` per-vnet breakout has no console UI (Phase 6.1+); same-hypervisor routing uses link type `local` only.
- **Integration tests** do not POST links or assert reconcile-to-`connected` (smoke only).

## Related docs

- [ADR 0012](../architecture/adrs/0012-hybrid-breakout-and-network-linking.md)
- [ADR 0004](../architecture/adrs/0004-kafka-event-bus.md)
- [docker-compose.md](../install/docker-compose.md)
