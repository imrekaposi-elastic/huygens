# ADR 0012: Hybrid breakout and network linking (Phase 6)

## Status

Accepted (Phase 6) — **MVP shipped**; GA criteria in [Phase 6 operations](../../operations/phase6-release-and-validation.md)

## Context

Operators need to connect libvirt virtual networks on different hypervisors (FRAMEWORK_PLAN: WireGuard breakout, centrally managed; drag-and-drop topology). Phase 4 IPAM assigns RFC1918 vnet CIDRs per project. The libvirt agent already applies WireGuard and flat L2 breakout locally (`breakout.json`, `wg-quick`). The control plane had no link model, no central keying, and no topology UI.

## Decision

### Hybrid model

| Component | Responsibility |
|-----------|----------------|
| **breakout-controller** (Go) | Build WG peer configs for a pairwise link from keys supplied by projects; no libvirt or JWT |
| **projects** (Python) | Desired state: `network_links`, overlay IPAM, RBAC, agent breakout proxy, reconcile loop |
| **libvirt agent** | Enforce breakout via `PUT .../breakout/wireguard` and `PUT .../breakout/flat` |
| **web** | Topology graph (React Flow); create/delete links; no private keys in browser |

### Link = one edge between two vnets

- Endpoints: `(agent_id, project_id, network_name)` × 2, same organization.
- **link_type `wireguard`:** different `agent_id` — overlay `/30` from `pool_kind=overlay`, breakout-controller `plan`, reconciler applies WG on both agents.
- **link_type `local`:** same `agent_id` — no WireGuard, no overlay allocation; reconciler applies flat `mode=local_peer` (iptables NAT exempt + FORWARD between peer vnet CIDRs). Requires agent build that accepts `local_peer` (see [operations doc](../../operations/phase6-release-and-validation.md)).
- **Overlay:** org `IpPool` with `pool_kind=overlay`; each wireguard link consumes one `/30`; tunnel addresses visible in API/UI.
- **Secrets:** WG private keys encrypted at rest (Fernet); never returned to clients.

### Lifecycle

`pending` → `applying` → `connected` | `error`; delete → `deleting` → removed. Reconciler runs in projects lifespan (default interval ~15s). Drift: compare agent breakout to expected; set `config_drift` on the link record. Console topology shows a **drift** badge on edges and in the link detail panel when `config_drift` is true (HTTP `GET .../topology`, not a Kafka consumer on `huy.network.links`).

### APIs

- JWT: `GET/POST/DELETE /api/v1/organizations/{org_id}/network-links`, `GET .../topology`
- Proxy: `GET/PUT .../projects/{pid}/agents/{aid}/networks/{name}/breakout(/wireguard|/flat)`
- Internal: breakout-controller `POST /v1/links/plan` (`X-Huy-Service-Token`)
- Internal: `POST /v1/links/revoke` — called for **WireGuard** link delete before agent breakout is disabled; **local** links skip revoke

### RBAC

- **Create/delete link:** `platform_admin`, org `admin`, or `operator` with operate on **both** projects.
- **View topology/links:** project read / org inventory read (same as networks).

### Events

- CloudEvents type `com.huygens.network.link.v1` on Kafka topic **`huy.network.links`** when link status changes ([ADR 0004](0004-kafka-event-bus.md)). Created by Compose `kafka-init` in the default stack; external clusters use [init-topics.sh](../../../docker/kafka/init-topics.sh).
- Console live refresh: inventory SSE + HTTP invalidation on projects mutations; link status also visible via topology API (`config_drift`, `last_error`). **No** Kafka consumer on `huy.network.links` in MVP — see [05-event-flow.excalidraw](../diagrams/05-event-flow.excalidraw).

### Deployment boundary

- Control plane (Compose): `projects`, `breakout-controller`, `web`, PostgreSQL, Kafka.
- **Libvirt agent is not in Compose** — must be installed and upgraded on each hypervisor with the same release as control plane for local links and metadata purge on network delete.

### Phase 6.1 — Per-vnet flat L2 console UI (shipped)

- Console: **Flat breakout** on project virtual networks (`bridge_uplink`, `macvlan`) via projects proxy → agent `PUT .../breakout/flat`.
- `local_peer` flat mode remains topology-managed only (read-only in UI when a `local` link is active).

### Out of scope (Phase 6 MVP)

- Cross-host **data-plane** automated test (control-plane reconcile is covered by unit tests; see [operations doc](../../operations/phase6-release-and-validation.md)).
- Elasticsearch / audit consumer for `huy.network.links` (topic is publish-only in MVP).

## Consequences

- Requires overlay pool per org before **cross-hypervisor** linking (UI guides creation). Same-hypervisor links need routable vnet CIDRs on both networks only.
- Second hypervisor agent needed for cross-host **data-plane** validation (manual runbook).
- Single-agent environments: cross-agent links remain `error` until a peer agent exists — expected, not a reconciler bug.
- Full mesh is emergent (many links), not auto-wired.
- Network delete via projects is allowed only when no VMs, active topology links, or enabled breakout remain on that vnet (**409** otherwise). Operators remove links in Topology and disable breakout first. See [phase7 operations](../../operations/phase7-compliance-and-lifecycle-guards.md) and agent `delete_network`.

## Alternatives considered

- **Projects-only keygen (no Go service):** Rejected; roadmap specifies `breakout-controller` and separates crypto from Python CRUD.
- **Browser → agent breakout:** Rejected; violates Phase 5 control-plane-only console rule.
- **Publishing link events to `huy.audit.events`:** Rejected for MVP; dedicated topic keeps audit vs operational link streams separable.
