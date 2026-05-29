# Phase 9 — Audited SSH gateway

Operational guide for Phase 9 **audited VM SSH**. Architecture: [ADR 0014](../architecture/adrs/0014-ssh-gateway-and-session-recording.md).

## Components

| Component | Port | Role |
|-----------|------|------|
| `ssh-gateway` (Go) | 8087 | JWT auth, session API, PTY recording, Kafka events |
| IAM SSH policy | 8081 | Account mappings, access groups, sudo rules, org SSH CA |
| libvirt agent relay | 9122 | Hypervisor-local TCP relay to guest `:22` |
| Inventory | 8083 | Internal `/internal/v1/ssh/target` resolution |
| Logstash (observability profile) | — | `huy.session.events` → `huy-sessions-*` |

## Local stack

```bash
docker compose up -d --build ssh-gateway iam inventory
# Optional ES ingest:
docker compose --profile observability up -d logstash
```

## Policy setup (FreeIPA-style)

1. **Org SSH CA** — auto-created on first `GET /api/v1/organizations/{org}/ssh/ca`.
2. **Account mapping** — `POST .../ssh/account-mappings` maps Huygens user → `linux_username`.
3. **Access group** — bind users or IdP group names; attach **sudo rules** with command allow lists.
4. **VM trust** — agent `PUT /api/v1/vms/{name}/ssh-trust` (or cloud-init on create) installs CA + sudoers.
5. **Project RBAC** — grant `ssh_access` role on the project.

## Client access

```bash
export HUY_ACCESS_TOKEN="<jwt>"
export HUY_ORG_ID="<org-uuid>"
./tools/huy-cli/huy ssh web-01 --project <project-uuid>
```

OpenSSH:

```bash
ssh -o ProxyCommand="./tools/huy-cli/huy ssh-proxy %h %p" user@vm-name.huygens
```

Console: **SSH access** → session list and asciicast replay download.

## Session pipeline

- Metadata: Kafka topic `huy.session.events` (CloudEvents `com.huygens.session.v1`).
- Recordings: asciicast v2 on gateway volume (`SSH_RECORDING_DIR`) + `recording_uri` in events.
- Search: Kibana Discover on `huy-sessions-*`, filter `event_kind:session`.

## Security notes

- Admins use the same gateway; all sessions recorded.
- `auditor` role: `ssh:session_read` only (list/replay), not `ssh:connect`.
- Relay validates HMAC session tokens (`SSH_GATEWAY_SERVICE_TOKEN`); no direct guest SSH from users when relay-only firewall is enabled on the hypervisor.

## Work packages (P9-0 … P9-9)

See [PHASED_PLAN.md](../PHASED_PLAN.md) Phase 9 section for delivery checklist.
