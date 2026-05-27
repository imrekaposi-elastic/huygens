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
| **Hypervisor agent** | WG + `local_peer` breakout; projects preflight via `GET /api/v1/agent` capabilities | Zero-touch upgrade |
| **Validation** | Unit tests + integration **API smoke**; manual two-agent WG runbook | Automated cross-host data-plane proof |
| **Events** | Publish to `huy.network.links` via `kafka-init` in Compose | ES consumer (future) |

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

**Docker Compose:** the `kafka-init` service creates this topic (and other `huy.*` topics)
automatically on `docker compose up`. No manual `kafka-topics.sh` step for the default stack.

**External Kafka:** run [`docker/kafka/init-topics.sh`](../../docker/kafka/init-topics.sh) with
`KAFKA_BOOTSTRAP` set to your brokers.

## Manual validation

| Scenario | Runbook |
|----------|---------|
| Cross-hypervisor WireGuard link | [tests/integration/README.md](../../tests/integration/README.md#manual-two-agent-wireguard-link-test-phase-6) |
| Same-hypervisor local link | [tests/integration/README.md](../../tests/integration/README.md#manual-same-hypervisor-local-link-test-phase-6) |
| Network delete / inventory orphan | Delete via **Projects → networks** only when no VMs, topology links, or active breakout use the vnet (**409** otherwise). See [phase7-compliance-and-lifecycle-guards.md](phase7-compliance-and-lifecycle-guards.md). Assignment reconciler (~60s) prunes OOB-deleted vnets from topology |

## Known limitations (documented backlog)

These are **not** fixed by documentation alone; tracked for product planning:

- **Flat L2** `bridge_uplink` / `macvlan`: configure per vnet in the console (**Networks → Flat breakout**, Phase 6.1). Same-hypervisor routing between vnets still uses topology link type `local` (`local_peer`).
- **Compose integration tests** are API smoke only (`tests/integration/test_network_links.py`). Control-plane reconcile-to-`connected` is covered in unit tests (`services/projects/tests/test_link_reconcile.py`).

## Related docs

- [phase7-compliance-and-lifecycle-guards.md](phase7-compliance-and-lifecycle-guards.md)
- [ADR 0012](../architecture/adrs/0012-hybrid-breakout-and-network-linking.md)
- [ADR 0004](../architecture/adrs/0004-kafka-event-bus.md)
- [docker-compose.md](../install/docker-compose.md)
