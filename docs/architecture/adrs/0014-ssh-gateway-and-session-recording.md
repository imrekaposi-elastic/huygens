# ADR 0014: SSH gateway and session recording (Phase 9)

## Status

Accepted (Phase 9)

## Context

Operators need audited SSH access to project VMs without granting hypervisor admin rights. Non-admin users with `ssh_access` must reach VMs (including sudo to allow-listed commands). Admins use the same gateway (`huy ssh`, Teleport-style). All sessions are recorded and searchable in Elasticsearch.

Guest VMs sit on NAT'd libvirt vnets; the control plane cannot dial guest `:22` directly.

## Decision

### Hybrid data path

| Component | Role |
|-----------|------|
| **`ssh-gateway`** (Go, `:8087`) | JWT auth, IAM authorize, PTY proxy, session recording, Kafka/object-store emit |
| **libvirt agent `ssh-relay`** | Hypervisor-local TCP relay to `guest_ip:22`; validates `X-Huy-Session-Token` |
| **IAM** | Account mappings, access groups, sudo rules, org SSH CA, internal authorize/sign APIs |
| **Inventory** | Resolve `(org, project, vm)` → `{agent_id, guest_ip, relay_url}` |

```text
Client → ssh-gateway → agent:9122 (relay) → VM:22
              ↓
     huy.session.events → Logstash → huy-sessions-*
     recording blob → object store (SeaweedFS)
```

### Identity and privilege (FreeIPA-inspired)

- **`SshAccountMapping`**: Huygens `user_id` → `linux_username` (org-scoped; optional `project_id`).
- **`SshAccessGroup`**: members by user id or IdP group name; binds to sudo rules.
- **`SshSudoRule`**: named rule with `command_allow_list` JSON and optional `sudoers_fragment`; pushed to VM as `/etc/sudoers.d/huy-<rule-id>`.
- **Host access (HBAC)**: `ssh_access` project role + VM assigned via `ProjectResource`.
- **Elevation**: sudo on guest only; gateway records PTY (Phase 14 adds keystroke allow-list enforcement).

### SSH CA trust

- One Ed25519 **org SSH CA** per organization (private key encrypted at rest in IAM).
- New VMs: cloud-init `#cloud-config` `ssh_ca` / `TrustedUserCAKeys` + users + sudoers from policy snapshot.
- Existing VMs: run the **guest onboard script** (`shared/huy_ssh_onboard`, API `.../ssh/guest-onboard`) on the workload — hypervisor-agnostic. Agent `PUT .../ssh-trust` stores a libvirt-local snippet only.
- Gateway signs short-lived user certificates (≤15 min) via IAM internal `sign-cert` API.

### Session pipeline

| Topic | Purpose |
|-------|---------|
| `huy.session.events` | Lifecycle metadata (CloudEvents) |
| `huy.session.recording` | PTY chunk pointers (optional; large blobs in object store) |

Elasticsearch index family: **`huy-sessions-*`**. Config audit stays on **`huy.audit.events`**.

### Security controls (MVP)

- No direct guest SSH from user workstations when relay-only mode enabled on agent.
- All sessions recorded (including admins); `auditor` has `ssh:session_read`, not `ssh:connect`.
- Session tokens single-use; service tokens for gateway ↔ IAM/agent.
- Recording URLs time-limited; CA keys never returned to clients.

### Out of scope (Phase 9 MVP)

- Gateway-side sudo/command enforcement (Phase 14 playbooks).
- MFA step-up at session create (stretch).
- K8s exec (Phase 13 reuses session index family).

## Consequences

- New Go service and agent relay port (`9122`) in deployment manifests.
- Org admins manage SSH policy in IAM; security engineers use `ssh:policy_manage`.
- Phase 13 k8s-access reuses ECS session document shape from this ADR.

## References

- [phase9-ssh-gateway.md](../../operations/phase9-ssh-gateway.md)
- [ADR 0004](0004-kafka-event-bus.md)
- [ADR 0008](0008-opentelemetry-and-edot.md)
- [PHASED_PLAN.md](../../PHASED_PLAN.md) Phase 9
