# Phase 9 — Audited SSH gateway

Operational guide for Phase 9 **audited VM SSH**. Architecture: [ADR 0014](../architecture/adrs/0014-ssh-gateway-and-session-recording.md).

## Components

| Component | Port | Role |
|-----------|------|------|
| `ssh-gateway` (Go) | 8087 | JWT auth, session API, SSH client bridge, PTY recording, Kafka events |
| IAM SSH policy | 8081 | Account mappings, access groups, sudo rules, org SSH CA |
| libvirt agent relay | 9122 | Hypervisor-local TCP relay to guest `:22` |
| Inventory | 8083 | Internal `/internal/v1/ssh/target` resolution |
| Logstash (observability profile) | — | Kafka → data stream `huy-sessions` |

## Local stack

```bash
docker compose up -d --build ssh-gateway iam inventory projects web
# Hypervisor: upgrade libvirt agent (ssh-relay + WebSocket relay on :8765/api/v1/ssh/relay/ws)
# Optional ES ingest:
docker compose --profile observability up -d logstash
```

**Vite dev console:** `cd web && npm install && npm run dev` — proxies `/api/v1/ssh` to `:8087` with WebSocket.

## Policy setup (FreeIPA-style)

1. **Org SSH CA** — auto-created on first `GET /api/v1/organizations/{org}/ssh/ca`.
2. **Account mapping** — `POST .../ssh/account-mappings` maps Huygens user → `linux_username`.
3. **Access group** — bind users or IdP group names; attach **sudo rules** with command allow lists.
4. **VM trust**
   - **New VMs:** projects merges org SSH CA + linux user into cloud-init on create.
   - **Existing VMs (any hypervisor):** download **Onboard script** from the console or
     `GET .../vms/{name}/guest-onboard` — run the script **on the guest as root** via your
     own admin path (console, CM, break-glass SSH). See [scripts/guest/README.md](../../scripts/guest/README.md).
   - Optional profile: `agents/libvirt/templates/cloud-init/huy-ssh-access.yaml`.
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
eval $(./tools/huy-cli/huy login -q platform-admin 'platform-admin-dev')
./tools/huy-cli/huy use
./tools/huy-cli/huy ssh
```

Or step by step: `huy orgs` → `huy org select` → `huy projects` → `huy project select` → `huy vms` → `huy ssh <vm>`.

### Console

1. **Projects** → select project → **VMs** → **Connect** (audited terminal).
2. **SSH access** → session list, **Play** (in-browser asciicast), **Download**, **Open** on active sessions.
3. **New VMs:** cloud-init profile + **Merge org SSH CA** (default on).
4. **Existing VMs:** **Onboard script** → copy to guest → `sudo bash huy-ssh-onboard-*.sh` (works on any hypervisor).

## Session pipeline

- **Metadata:** Kafka `huy.session.events` → Logstash → data stream `huy-sessions` (pipeline `huy-sessions-ecs`).
- **Terminal I/O:** On disconnect, gateway publishes line-batched events to `huy.session.recording` → same data stream `huy-sessions` (pipeline `huy-session-terminal`). Search `terminal.plaintext`.
- **Recordings (replay):** asciicast v2 on gateway volume (`SSH_RECORDING_DIR`) + `huy.recording.uri` in events.
- **Search:** Kibana Discover → data view **Huy SSH Sessions** (`huy-sessions`), filter `session.id`.

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
5. Optional: `docker compose --profile observability` and confirm data stream `huy-sessions` in Kibana (filter `session.id:<uuid>`).

## Work packages (P9-0 … P9-9)

See [PHASED_PLAN.md](../PHASED_PLAN.md) Phase 9 section for delivery checklist.
