# Architecture diagrams

Excalidraw source files for Huygens. Open in [excalidraw.com](https://excalidraw.com) (File → Open) or the VS Code Excalidraw extension.

| File | Topic |
|------|--------|
| [01-system-context.excalidraw](01-system-context.excalidraw) | C4-style context: console → IAM, projects, inventory, **compliance**; object store for GRC artifacts |
| [02-deployment.excalidraw](02-deployment.excalidraw) | Compose/K8s deployment incl. **huy-compliance :8086** and object store |
| [03-tenancy.excalidraw](03-tenancy.excalidraw) | Tenancy: placement profiles (catalog + characteristics), **huy-compliance**, criticality |
| [04-agent-dual-io.excalidraw](04-agent-dual-io.excalidraw) | Libvirt write queue vs read path |
| [05-event-flow.excalidraw](05-event-flow.excalidraw) | Kafka topics, producers, and consumers (incl. `huy.network.links`) |
| [06-phase-roadmap.excalidraw](06-phase-roadmap.excalidraw) | Phases 0–17 — **Phase 7 Compliance + GRC** marked complete (yellow) |
| [07-air-gapped.excalidraw](07-air-gapped.excalidraw) | Offline install topology (control plane includes Compliance) |

Regenerate from repo root after editing the builder:

```bash
python3 scripts/generate-excalidraw-diagrams.py
```

Edit `scripts/generate-excalidraw-diagrams.py` (`diagram_*` functions), then re-run. Refine layout in Excalidraw after import if needed.

Phase 7 scope in prose: [operations/phase7-compliance-and-lifecycle-guards.md](../../operations/phase7-compliance-and-lifecycle-guards.md) · [compliance/README.md](../../compliance/README.md).
