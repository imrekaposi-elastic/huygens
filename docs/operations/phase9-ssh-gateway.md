# Phase 9 — Audited SSH gateway

Operational guide for Phase 9 **audited VM SSH**. Architecture: [ADR 0014](../architecture/adrs/0014-ssh-gateway-and-session-recording.md).

## Components

| Component | Port | Role |
|-----------|------|------|
| `ssh-gateway` (Go) | 8087 | JWT auth, session API, SSH client bridge, PTY recording, Kafka events |
| IAM SSH policy | 8081 | Account mappings, access groups, sudo rules, org SSH CA |
| libvirt agent relay | 9122 | Hypervisor-local TCP relay to guest `:22` |
| Inventory | 8083 | Internal `/internal/v1/ssh/target` resolution |
| Logstash (observability profile) | — | `huy.session.events` → `huy-sessions-*` |

## Local stack

```bash
docker compose up -d --build ssh-gateway iam inventory projects web
# Hypervisor: upgrade libvirt agent (ssh-relay on 9122)
# Optional ES ingest:
docker compose --profile observability up -d logstash
```

**Vite dev console:** `cd web && npm install && npm run dev` — proxies `/api/v1/ssh` to `:8087` with WebSocket.

## Policy setup (FreeIPA-style)

1. **Org SSH CA** — auto-created on first `GET /api/v1/organizations/{org}/ssh/ca`.
2. **Account mapping** — `POST .../ssh/account-mappings` maps Huygens user → `linux_username`.
3. **Access group** — bind users or IdP group names; attach **sudo rules** with command allow lists.
4. **VM trust** — console **SSH trust** on project VM row (`POST .../ssh-trust/setup` via projects → IAM CA + agent), agent `PUT /api/v1/vms/{name}/ssh-trust`, or cloud-init on create.
5. **Project RBAC** — grant `ssh_access` role on the project.

**Dev bootstrap (one shot):**

```bash
export HUY_ORG_ID=...
export HUY_PROJECT_ID=...
export HUY_AGENT_ID=...
export HUY_VM_NAME=...
export HUY_LINUX_USER=ubuntu
export HUY_AGENT_URL=http://<hypervisor>:9100
./scripts/ssh-bootstrap-dev.sh
```

## Client access

### CLI

```bash
pip install -r tools/huy-cli/requirements.txt
eval $(./tools/huy-cli/huy login -q platform-admin 'platform-admin-secret-12' --org "$HUY_ORG_ID")
export HUY_SSH_GATEWAY_URL=http://127.0.0.1:5173   # Vite dev, or :8087 direct
./tools/huy-cli/huy ssh web-01 --project "$HUY_PROJECT_ID"
```

### Console

1. **Projects** → select project → **VMs** → **Connect** (audited terminal).
2. **SSH access** → session list, replay download, **Open** on active sessions.

## Session pipeline

- Metadata: Kafka topic `huy.session.events` (CloudEvents `com.huygens.session.v1`).
- Recordings: asciicast v2 on gateway volume (`SSH_RECORDING_DIR`) + `recording_uri` in events.
- Search: Kibana Discover on `huy-sessions-*`, filter `event_kind:session`.

## Security notes

- Admins use the same gateway; all sessions recorded.
- `auditor` role: `ssh:session_read` only (list/replay), not `ssh:connect`.
- Relay validates HMAC session tokens (`SSH_GATEWAY_SERVICE_TOKEN`).
- Gateway runs a real **SSH client** with IAM-signed user certificates (not raw TCP to port 22).
- Browser WebSocket passes JWT via `?access_token=` on upgrade (browsers cannot set `Authorization` on WS).

## Test plan (sign-off)

1. Stack up: `ssh-gateway`, `iam`, `inventory`, `projects`, `web`; libvirt agent with relay on hypervisor.
2. Run `scripts/ssh-bootstrap-dev.sh` (or console **SSH trust** + IAM mapping manually).
3. **Console:** Projects → VM → **Connect** → shell works; session on `/access` with recording after disconnect.
4. **CLI:** `huy login` → `huy ssh VM --project ID` → interactive shell.
5. Optional: `docker compose --profile observability` and confirm `huy-sessions-*` in Kibana.

## Work packages (P9-0 … P9-9)

See [PHASED_PLAN.md](../PHASED_PLAN.md) Phase 9 section for delivery checklist.
