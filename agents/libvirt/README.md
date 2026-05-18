# huy-libvirt-agent

KVM hypervisor agent exposing a REST API for VM lifecycle, virtual networks, WireGuard/flat breakout, DNAT, cloud-init, and observability.

Monorepo path: `agents/libvirt/` (from repository root: `make -C agents/libvirt <target>` or use the root `Makefile`).

## Features

- **VMs**: create (cloud-init + qcow2 overlay), list, update, delete; status `off` / `on` / `degraded` (TCP :22 probe)
- **Networks**: CRUD, WireGuard and flat L2 breakout, scoped nftables SNAT/DNAT
- **Agent settings**: `country`, `city`, `company` inherited on all created resources
- **Observability**: structlog JSON, OpenTelemetry, append-only audit log, CloudEvents file publisher
- **API docs**: Swagger UI at `/docs`, ReDoc at `/redoc`, exportable OpenAPI schema

## Host prerequisites

See [docs/host-requirements.md](docs/host-requirements.md) for per-distribution package lists.

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
| `HUY_AGENT_COUNTRY` | Inherited label (required) |
| `HUY_AGENT_CITY` | Inherited label (required) |
| `HUY_AGENT_COMPANY` | Inherited label (required) |
| `HUY_DATA_DIR` | State directory (default `/var/lib/huy-libvirt-agent`) |
| `LIBVIRT_URI` | libvirt connection (default `qemu:///system`) |

See [config.example.yaml](config.example.yaml) and [.env.example](.env.example).

## Run

```bash
export $(grep -v '^#' .env | xargs)
huy-libvirt-agent
# or: uvicorn huy_libvirt_agent.main:app --host 127.0.0.1 --port 8765
```

API documentation: http://127.0.0.1:8765/docs

## systemd

```bash
sudo cp systemd/huy-libvirt-agent.service /etc/systemd/system/
sudo mkdir -p /etc/huy-libvirt-agent
sudo cp config.example.yaml /etc/huy-libvirt-agent/config.yaml
# create /etc/huy-libvirt-agent/env with secrets
sudo systemctl enable --now huy-libvirt-agent
```

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
| GET/POST | `/api/v1/vms` | List / create VMs |
| GET/PATCH/DELETE | `/api/v1/vms/{name}` | VM operations |
| GET/POST | `/api/v1/networks` | List / create vnets |
| PUT | `/api/v1/networks/{name}/breakout/wireguard` | WireGuard breakout |
| PUT | `/api/v1/networks/{name}/breakout/flat` | Flat L2 breakout |
| GET/POST/DELETE | `/api/v1/networks/{vnet}/dnat` | DNAT rules |

All `/api/v1/*` routes require `Authorization: Bearer <token>`.

Optional headers: `X-Request-Id`, `X-Actor`.

## License

MIT
