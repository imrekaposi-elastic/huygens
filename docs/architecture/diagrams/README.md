# Architecture diagrams

Excalidraw source files for Huygens. Open in [excalidraw.com](https://excalidraw.com) (File → Open) or the VS Code Excalidraw extension.

| File | Topic |
|------|--------|
| [01-system-context.excalidraw](01-system-context.excalidraw) | C4-style system context (operators → **Projects** proxy) |
| [02-deployment.excalidraw](02-deployment.excalidraw) | Physical / K8s deployment |
| [03-tenancy.excalidraw](03-tenancy.excalidraw) | Org, project, agent hierarchy |
| [04-agent-dual-io.excalidraw](04-agent-dual-io.excalidraw) | Libvirt write queue vs read path |
| [05-event-flow.excalidraw](05-event-flow.excalidraw) | Kafka topics and producers |
| [06-phase-roadmap.excalidraw](06-phase-roadmap.excalidraw) | Delivery phases 0–13 |
| [07-air-gapped.excalidraw](07-air-gapped.excalidraw) | Offline install topology |

Regenerate from repo root:

```bash
python3 scripts/generate-excalidraw-diagrams.py
```

Edit the builder functions in that script, then re-run. You can refine layout further in Excalidraw after import.
