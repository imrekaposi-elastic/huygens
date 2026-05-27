# Control plane services

Microservices for the Huygens platform. Each service is an independent Python package.

| Service | Phase | Purpose |
|---------|-------|---------|
| [iam](iam/) | 1a ✅ | Local auth, users, roles, JWT |
| [registry](registry/) | 1 | Agent enrollment, token vault, provider/region |
| [inventory](inventory/) | 1 | Poll agents, desired vs actual state, Kafka publish |
| [projects](projects/) | 3–6 ✅ | Projects, IPAM, network links, agent proxy, delete guards |
| [breakout-controller](breakout-controller/) | 6 ✅ | WireGuard link planning (internal, Go) |
| [compliance](compliance/) | 7 ✅ | Org catalog, explorer, criticality, infrastructure standards |

Phase 0 provides health-check scaffolds only. Operations: [phase6](../docs/operations/phase6-release-and-validation.md), [phase7](../docs/operations/phase7-compliance-and-lifecycle-guards.md). See [docs/architecture/README.md](../docs/architecture/README.md).

**Docker Compose:** from repo root, `docker compose up -d --build` — see [docs/install/docker-compose.md](../docs/install/docker-compose.md).
