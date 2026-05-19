# Control plane services

Microservices for the Huygens platform. Each service is an independent Python package.

| Service | Phase | Purpose |
|---------|-------|---------|
| [iam](iam/) | 1a ✅ | Local auth, users, roles, JWT |
| [registry](registry/) | 1 | Agent enrollment, token vault, provider/region |
| [inventory](inventory/) | 1 | Poll agents, desired vs actual state, Kafka publish |

Phase 0 provides health-check scaffolds only. See [docs/architecture/README.md](../docs/architecture/README.md).

**Docker Compose:** from repo root, `docker compose up -d --build` — see [docs/install/docker-compose.md](../docs/install/docker-compose.md).
