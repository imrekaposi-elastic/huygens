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
| `HUY_AGENT_TOKEN` | API bearer token (required) |
| `HUY_CLOUD_INIT_VALIDATION` | `off`, `basic`, or `schema` (default; requires `cloud-init` OS package) |
| `HUY_PUBLIC_BASE_URL` | Optional public URL for Swagger (default: same host as `/docs`) |
| `HUY_CORS_ORIGINS` | Comma-separated origins if calling the API from another web app |
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
