# ADR 0009: Air-gapped installation

## Status

Accepted (Phase 0)

## Context

Government and critical infrastructure require offline install — same strategic thread as open source and self-hosted agents.

## Decision

- No mandatory call-home to Elastic Cloud or Huygens SaaS.
- Deliver **offline artifacts**: container images, Helm chart, tarball + `docs/install/air-gapped.md`.
- **Bring-your-own** PostgreSQL and **Kafka** (required for standard control-plane stack per ADR 0004). Elasticsearch optional (audit/compliance).
- **Degraded air-gap:** documented poll-only path without Kafka (not the default Compose stack).
- Agent runs on hypervisor with local `data_dir`; TLS optional.
- Inventory poller uses only internal agent URLs.

## Consequences

- Phase 11 documents verification checklist.
- License Apache 2.0 allows offline redistribution of binaries/images.

See [../../install/air-gapped.md](../../install/air-gapped.md).
