# ADR 0012: Hybrid breakout and network linking (Phase 6)

## Status

Accepted (Phase 6)

## Context

Operators need to connect libvirt virtual networks on different hypervisors (FRAMEWORK_PLAN: WireGuard breakout, centrally managed; drag-and-drop topology). Phase 4 IPAM assigns RFC1918 vnet CIDRs per project. The libvirt agent already applies WireGuard and flat L2 breakout locally (`breakout.json`, `wg-quick`). The control plane had no link model, no central keying, and no topology UI.

## Decision

### Hybrid model

| Component | Responsibility |
|-----------|----------------|
| **breakout-controller** (Go) | Generate WG key pairs; build peer configs for a pairwise link; no libvirt or JWT |
| **projects** (Python) | Desired state: `network_links`, overlay IPAM, RBAC, agent breakout proxy, reconcile loop |
| **libvirt agent** | Enforce breakout via existing `PUT .../breakout/wireguard` |
| **web** | Topology graph (React Flow); create/delete links; no private keys in browser |

### Link = one edge between two vnets

- Endpoints: `(agent_id, project_id, network_name)` × 2, same organization.
- **link_type:** `wireguard` when endpoints are on **different** hypervisors (overlay `/30`, breakout-controller plan). **`local`** when both vnets share the same `agent_id`: no WireGuard, no overlay allocation; reconciler applies flat breakout `mode=local_peer` (iptables NAT exempt + FORWARD between peer vnet CIDRs on that agent).
- **Overlay:** org `IpPool` with `pool_kind=overlay`; each link consumes one `/30`; tunnel addresses visible in API/UI.
- **Secrets:** WG private keys encrypted at rest (`huy_auth.agent_tokens` Fernet); never returned to clients.

### Lifecycle

`pending` → `applying` → `connected` | `error`; delete → `deleting` → removed. Reconciler runs in projects lifespan (interval ~10s). Drift: compare agent breakout peers to expected; set `config_drift` on link.

### APIs

- JWT: `GET/POST/DELETE /api/v1/organizations/{org_id}/network-links`, `GET .../topology`
- Proxy: `GET/PUT .../projects/{pid}/agents/{aid}/networks/{name}/breakout(/wireguard|/flat)`
- Internal: breakout-controller `POST /v1/links/plan`, `POST /v1/links/revoke` (`X-Huy-Service-Token`)

### RBAC

- **Create/delete link:** `platform_admin`, org `admin`, or `operator` with operate on **both** projects.
- **View topology/links:** project read / org inventory read (same as networks).

### Events

- CloudEvents type `com.huygens.network.link.v1` on topic `huy.audit.events` (MVP) when link status changes; console refreshes via existing inventory SSE invalidation on projects mutations.

## Consequences

- Requires overlay pool per org before **cross-hypervisor** linking (UI guides creation). Same-hypervisor links need only routable vnet CIDRs on both networks.
- Second hypervisor agent needed for real cross-host validation.
- Full mesh is emergent (many links), not auto-wired.

## Alternatives considered

- **Projects-only keygen (no Go service):** Rejected; roadmap specifies `breakout-controller` and separates crypto from Python CRUD.
- **Browser → agent breakout:** Rejected; violates Phase 5 control-plane-only console rule.
