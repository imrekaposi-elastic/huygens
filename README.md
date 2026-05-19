# Huygens

Open-source infrastructure operations platform: **know where** workloads run and **why**
they are placed there. Apache License 2.0.

| Path | Description |
|------|-------------|
| [agents/libvirt](agents/libvirt/) | KVM hypervisor agent (REST API, libvirt, networking) |
| [services/](services/) | Control plane: IAM, registry, inventory (scaffolds) |
| [web/](web/) | Console SPA (Phase 5 placeholder) |
| [schemas/kafka/](schemas/kafka/) | CloudEvents JSON schemas |
| [docs/architecture/](docs/architecture/) | ADRs, ERD, Excalidraw diagrams |
| [docs/install/air-gapped.md](docs/install/air-gapped.md) | Offline installation guide |
| [FRAMEWORK_PLAN.md](FRAMEWORK_PLAN.md) | Product scope and non-functional requirements |
| [docs/PHASED_PLAN.md](docs/PHASED_PLAN.md) | Phased delivery roadmap (0–13) |

## Quick start (libvirt agent)

```bash
cd agents/libvirt
cp .env.example .env
make install
make run
```

See [agents/libvirt/README.md](agents/libvirt/README.md).

## Local mock stack (Docker Compose)

```bash
cp compose.env.example .env
docker compose up -d --build
# IAM http://localhost:8081/docs  ·  registry :8082  ·  inventory :8083
```

See [docs/install/docker-compose.md](docs/install/docker-compose.md).

## Control plane

**IAM (Phase 1a):**

```bash
cd services/iam && cp .env.example .env && make install && make run   # :8081
```

**Registry / inventory (Phase 0 scaffolds):**

```bash
cd services/registry && pip install -e . && huy-registry    # :8082
cd services/inventory && pip install -e . && huy-inventory  # :8083
```

## Contributing

[CONTRIBUTING.md](CONTRIBUTING.md) · [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) · [LICENSE](LICENSE)

## Phases

Phase **0** (this repo state): monorepo layout, ADRs, Kafka schemas, service scaffolds.

Phase **1a/1b/1**: IAM, agent dual I/O completion, registry + inventory poll.

See [architecture README](docs/architecture/README.md) and [phased plan](docs/PHASED_PLAN.md).
