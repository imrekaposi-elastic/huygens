# huy-libvirt-agent

KVM hypervisor agent exposing a REST API for VM lifecycle, virtual networks, WireGuard/flat breakout, DNAT, cloud-init, and observability.

Monorepo path: `agents/libvirt/` (from repository root: `make -C agents/libvirt <target>` or use the root `Makefile`).

## Features

- **VMs**: create (cloud-init + qcow2 overlay), list, update, delete; status `off` / `on` / `degraded` (TCP :22 probe)
- **Networks**: CRUD, WireGuard and flat L2 breakout, scoped nftables SNAT/DNAT
- **Agent settings**: `country`, `city`, `company` inherited on all created resources
- **Observability**: structlog JSON, OpenTelemetry, Prometheus `/metrics` (host CPU/memory/disk + per-VM libvirt stats), append-only audit log, CloudEvents file publisher
- **API docs**: Swagger UI at `/docs`, ReDoc at `/redoc`, exportable OpenAPI schema

## Host prerequisites

See [docs/host-requirements.md](docs/host-requirements.md) for per-distribution package lists.

The **`cloud-init`** OS package is required (schema validation and `cloud-init schema` CLI). Package list: [requirements-host.txt](requirements-host.txt).

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,libvirt]"
cp .env.example .env   # edit HUY_AGENT_TOKEN and agent settings
```

## Configure

Environment variables (or `/etc/huy-libvirt-agent/config.yaml`):

| Variable | Description |
|----------|-------------|
| `HUY_AGENT_TOKEN` | API bearer token(s); comma-separated list allowed |
| `HUY_AGENT_TOKENS` | Additional bearer tokens (comma- or newline-separated) |
| `HUY_CLOUD_INIT_VALIDATION` | `off`, `basic`, or `schema` (default; requires `cloud-init` OS package) |
| `HUY_PUBLIC_BASE_URL` | Optional public URL for Swagger (default: same host as `/docs`) |
| `HUY_CORS_ORIGINS` | Comma-separated origins if calling the API from another web app |
| `HUY_LIBVIRT_QUEUE_WORKERS` | Write-path worker threads (default `1` — serializes mutations) |
| `HUY_LIBVIRT_QUEUE_MAX_PENDING` | Max queued write-path libvirt calls before HTTP 503 |
| `HUY_LIBVIRT_QUEUE_TIMEOUT_SECONDS` | Write-path queue + execution timeout |
| `HUY_LIBVIRT_READ_QUEUE_WORKERS` | Read-path workers for list/state/metrics (default `2`) |
| `HUY_LIBVIRT_READ_QUEUE_MAX_PENDING` | Max queued read-path calls before HTTP 503 |
| `HUY_LIBVIRT_READ_QUEUE_TIMEOUT_SECONDS` | Read-path queue timeout (default `120`) |
| `HUY_STATUS_POLL_SECONDS` | VM status monitor interval (default `30`, min `10`) |
| `HUY_AGENT_COUNTRY` | Inherited label (required) |
| `HUY_AGENT_CITY` | Inherited label (required) |
| `HUY_AGENT_COMPANY` | Inherited label (required) |
| `HUY_DATA_DIR` | State directory (default `/var/lib/huy-libvirt-agent`) |
| `LIBVIRT_URI` | libvirt connection (default `qemu:///system`) |
| `HUY_TLS_ENABLED` | Serve API over HTTPS (default `false`) |
| `HUY_TLS_AUTO_GENERATE` | Create CA + server cert under `{data_dir}/tls` if missing (default `true`) |

See [config.example.yaml](config.example.yaml) and [.env.example](.env.example).

## TLS (HTTPS)

When `HUY_TLS_ENABLED=true`, the agent generates (or reuses) a private CA and server certificate on startup:

- Files: `{data_dir}/tls/ca.pem`, `server.crt`, `server.key` (keys are mode `0600`)
- Control plane: trust `ca.pem` once, then call `https://<host>:8765/...`
- Bootstrap CA via API: `GET /api/v1/agent/tls/ca` (bearer auth required)
- Fingerprint: `GET /api/v1/agent` → `tls.ca_fingerprint_sha256`

```bash
# Fetch CA (after first HTTPS start with a token)
curl -k -H "Authorization: Bearer $TOKEN" https://dommel.kaposi.net:8765/api/v1/agent/tls/ca -o huy-agent-ca.pem

# Subsequent requests
curl --cacert huy-agent-ca.pem -H "Authorization: Bearer $TOKEN" https://dommel.kaposi.net:8765/api/v1/agent
```

Set `HUY_TLS_REGENERATE=true` once to rotate CA and server certificate.

## Run

```bash
export $(grep -v '^#' .env | xargs)
huy-libvirt-agent
# or: uvicorn huy_libvirt_agent.main:app --host 127.0.0.1 --port 8765
```

API documentation: `http://127.0.0.1:8765/docs` (or `https://...` when TLS is enabled)

## Observability (Phase 8)

- **Prometheus:** `GET /metrics` on the agent (host CPU/memory/disk, libvirt queues, per-VM stats).
- **OpenTelemetry:** set `OTEL_EXPORTER_OTLP_ENDPOINT` (and optional `OTEL_SERVICE_NAME`, default `huy-libvirt-agent`) to export HTTP traces and the same hypervisor metrics over OTLP on an interval aligned with `HUY_STATUS_POLL_SECONDS`.
- **Logs:** JSON to stdout/journal with ECS-style fields (`service.name`, `trace.id`, `@timestamp`). See [phase8-observability.md](../../docs/operations/phase8-observability.md).

```bash
curl -i http://127.0.0.1:8765/healthz   # expect X-Request-Id (and X-Trace-Id when OTLP/tracing is active)
```

## Upgrading the agent (Phase 6+)

The control plane (Compose) and the libvirt agent **release together** for breakout and
topology features. After `git pull` on the control plane host, upgrade every hypervisor
that participates in network links.

### Sync hypervisor git checkout (e.g. dommel)

If `git pull` fails with local changes to `path_safety.py`, `image_service.py`, etc., the
hypervisor likely has **old manual patches** from before those fixes landed on `main`. The
repository already contains the full versions — do not try to merge dommel’s copies.

From the repo root on the hypervisor:

```bash
sudo bash /opt/huygens/scripts/sync-hypervisor-repo.sh /opt/huygens
```

Or manually:

```bash
cd /opt/huygens
git fetch origin
git reset --hard origin/main
git clean -fd
cd agents/libvirt && python3 -m pip install -e ".[libvirt]"
sudo systemctl restart huy-libvirt-agent
```

```bash
# On the hypervisor (e.g. /opt/huygens) after git is on origin/main
# huy-telemetry is a monorepo package — install it before the agent (plain pip cannot resolve [tool.uv.sources])
python3 -m pip install -e /opt/huygens/shared/huy_telemetry
cd /opt/huygens/agents/libvirt
python3 -m pip install -e ".[libvirt]"
sudo systemctl restart huy-libvirt-agent
```

Verify `local_peer` is supported (required for same-hypervisor links):

```bash
python3 -c "from huy_libvirt_agent.api.schemas.network import FlatBreakoutConfig; \
print(FlatBreakoutConfig.model_json_schema()['properties']['mode'])"
```

Expected: enum includes `bridge_uplink`, `macvlan`, **`local_peer`**.

Full checklist: [docs/operations/phase6-release-and-validation.md](../../docs/operations/phase6-release-and-validation.md).

**Network delete:** operator delete via projects removes libvirt definition and agent-managed
metadata under `data_dir/vnets/{name}/` so inventory does not list ghost vnets.

## systemd

From the hypervisor (repo at `/opt/huygens`):

```bash
sudo bash /opt/huygens/agents/libvirt/scripts/install-systemd.sh
```

Or manually: copy `systemd/huy-libvirt-agent.service`, ensure `/etc/huy-libvirt-agent/env` exists, then `systemctl enable --now huy-libvirt-agent`.

Logs: `journalctl -u huy-libvirt-agent -f`

## Development

```bash
make dev
make test
make openapi   # writes openapi/openapi.json
make lint
```

## API overview

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/agent` | Agent settings |
| GET/POST | `/api/v1/images` | List / register managed base images |
| GET/PATCH/DELETE | `/api/v1/images/{name}` | Image operations |
| GET/POST | `/api/v1/cloud-init` | List / create cloud-init profiles |
| POST | `/api/v1/cloud-init/validate` | Validate cloud-init without saving (422 + issues on failure) |
| GET/PATCH/DELETE | `/api/v1/cloud-init/{name}` | Cloud-init profile operations |
| GET/POST | `/api/v1/vms` | List / create VMs |
| GET/PATCH/DELETE | `/api/v1/vms/{name}` | VM operations |
| GET/POST | `/api/v1/networks` | List / create vnets |
| PUT | `/api/v1/networks/{name}/breakout/wireguard` | WireGuard breakout |
| PUT | `/api/v1/networks/{name}/breakout/flat` | Flat L2 breakout |
| GET/POST/DELETE | `/api/v1/networks/{vnet}/dnat` | DNAT rules |

| GET | `/metrics` | Prometheus text (no auth); host + VM resource metrics |

All `/api/v1/*` routes require `Authorization: Bearer <token>`.

Optional headers: `X-Request-Id`, `X-Actor`.

### Prometheus metrics (excerpt)

| Metric | Description |
|--------|-------------|
| `huy_host_cpu_usage_percent` | Host CPU utilization |
| `huy_host_memory_*_bytes` | Total / used / available RAM |
| `huy_host_disk_bytes{mount,kind}` | Disk total / used / free per mount |
| `huy_host_disk_*_total` | Cumulative disk I/O bytes and operations |
| `huy_vm_memory_used_bytes{vm}` | Per-VM memory (libvirt) |
| `huy_vm_block_*_bytes_total{vm,device}` | Per-VM disk I/O |
| `huy_vm_cpu_time_seconds_total{vm}` | Per-VM CPU time |

## License

MIT
